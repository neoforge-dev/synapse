"""HashiCorp Vault integration for enterprise key management."""

import base64
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import hvac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hvac.exceptions import VaultError

logger = logging.getLogger(__name__)


@dataclass
class VaultConfig:
    """Configuration for HashiCorp Vault integration."""
    url: str
    token: str | None = None
    role_id: str | None = None  # For AppRole authentication
    secret_id: str | None = None
    mount_point: str = "synapse-kv"
    namespace: str | None = None
    verify: bool = True
    timeout: int = 30
    max_retries: int = 3


class VaultKeyManager:
    """Enterprise key management using HashiCorp Vault."""

    def __init__(self, config: VaultConfig):
        """Initialize Vault key manager with configuration."""
        self.config = config
        self.client = self._initialize_vault_client()
        self.key_cache: dict[str, dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL

        # Performance metrics
        self.metrics = {
            "key_retrievals": 0,
            "key_creations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "vault_errors": 0,
            "total_vault_time": 0.0
        }

        logger.info(f"Initialized VaultKeyManager with mount point: {config.mount_point}")

    def _initialize_vault_client(self) -> hvac.Client:
        """Initialize and authenticate Vault client."""
        try:
            client = hvac.Client(
                url=self.config.url,
                verify=self.config.verify,
                timeout=self.config.timeout,
                namespace=self.config.namespace
            )

            # Authenticate based on available credentials
            if self.config.token:
                client.token = self.config.token
            elif self.config.role_id and self.config.secret_id:
                # Use AppRole authentication
                auth_response = client.auth.approle.login(
                    role_id=self.config.role_id,
                    secret_id=self.config.secret_id
                )
                client.token = auth_response['auth']['client_token']
            else:
                # Try to use VAULT_TOKEN environment variable
                token = os.getenv('VAULT_TOKEN')
                if not token:
                    raise ValueError("No Vault authentication credentials provided")
                client.token = token

            # Verify authentication
            if not client.is_authenticated():
                raise ValueError("Failed to authenticate with Vault")

            # Enable KV v2 secrets engine if not exists
            try:
                client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path=self.config.mount_point,
                    options={'version': '2'}
                )
                logger.info(f"Enabled KV v2 secrets engine at {self.config.mount_point}")
            except VaultError as e:
                if "path is already in use" not in str(e):
                    logger.warning(f"Could not enable KV engine: {str(e)}")

            return client

        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {str(e)}")
            raise

    def create_master_key(self, tenant_id: UUID, key_type: str = "encryption") -> dict[str, Any]:
        """Create new master key for tenant."""
        start_time = time.time()

        try:
            # Generate AES-256 master key
            master_key = AESGCM.generate_key(bit_length=256)
            master_key_b64 = base64.b64encode(master_key).decode('ascii')

            key_metadata = {
                "tenant_id": str(tenant_id),
                "key_type": key_type,
                "algorithm": "AES-256",
                "created_at": datetime.utcnow().isoformat(),
                "version": 1,
                "status": "active",
                "rotation_schedule": "30d",
                "compliance_tags": ["FIPS-140-2", "Common-Criteria"],
                "key_usage": ["encryption", "decryption"]
            }

            # Store in Vault with versioning
            vault_path = f"tenants/{tenant_id}/master-keys/{key_type}"

            secret_data = {
                "key": master_key_b64,
                "metadata": key_metadata
            }

            # Create or update secret in Vault KV v2
            response = self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret=secret_data,
                mount_point=self.config.mount_point
            )

            # Update cache
            cache_key = f"{tenant_id}:{key_type}:master"
            self.key_cache[cache_key] = {
                "key": master_key,
                "metadata": key_metadata,
                "vault_version": response['data']['version'],
                "cached_at": time.time()
            }

            # Update metrics
            vault_time = time.time() - start_time
            self.metrics["key_creations"] += 1
            self.metrics["total_vault_time"] += vault_time

            logger.info(f"Created master key for tenant {tenant_id} in {vault_time*1000:.2f}ms")

            return {
                "key_id": f"{tenant_id}:{key_type}:master",
                "version": response['data']['version'],
                "created_at": key_metadata["created_at"],
                "status": "active"
            }

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to create master key for tenant {tenant_id}: {str(e)}")
            raise

    def get_master_key(self, tenant_id: UUID, key_type: str = "encryption") -> bytes:
        """Retrieve master key for tenant."""
        start_time = time.time()
        cache_key = f"{tenant_id}:{key_type}:master"

        # Check cache first
        if self._is_cache_valid(cache_key):
            self.metrics["cache_hits"] += 1
            return self.key_cache[cache_key]["key"]

        self.metrics["cache_misses"] += 1

        try:
            vault_path = f"tenants/{tenant_id}/master-keys/{key_type}"

            # Retrieve from Vault KV v2
            response = self.client.secrets.kv.v2.read_secret_version(
                path=vault_path,
                mount_point=self.config.mount_point
            )

            if not response or 'data' not in response or 'data' not in response['data']:
                raise ValueError(f"Master key not found for tenant {tenant_id}")

            secret_data = response['data']['data']
            master_key_b64 = secret_data["key"]
            master_key = base64.b64decode(master_key_b64)

            # Update cache
            self.key_cache[cache_key] = {
                "key": master_key,
                "metadata": secret_data["metadata"],
                "vault_version": response['data']['metadata']['version'],
                "cached_at": time.time()
            }

            # Update metrics
            vault_time = time.time() - start_time
            self.metrics["key_retrievals"] += 1
            self.metrics["total_vault_time"] += vault_time

            logger.debug(f"Retrieved master key for tenant {tenant_id} in {vault_time*1000:.2f}ms")
            return master_key

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to retrieve master key for tenant {tenant_id}: {str(e)}")
            raise

    def rotate_master_key(self, tenant_id: UUID, key_type: str = "encryption") -> dict[str, Any]:
        """Rotate master key for tenant."""
        start_time = time.time()

        try:
            # Get current key metadata
            vault_path = f"tenants/{tenant_id}/master-keys/{key_type}"
            current_response = self.client.secrets.kv.v2.read_secret_version(
                path=vault_path,
                mount_point=self.config.mount_point
            )

            if not current_response:
                raise ValueError(f"No existing master key found for tenant {tenant_id}")

            current_metadata = current_response['data']['data']['metadata']
            current_version = current_response['data']['metadata']['version']

            # Generate new master key
            new_master_key = AESGCM.generate_key(bit_length=256)
            new_master_key_b64 = base64.b64encode(new_master_key).decode('ascii')

            # Update metadata
            new_metadata = current_metadata.copy()
            new_metadata.update({
                "version": current_metadata["version"] + 1,
                "created_at": datetime.utcnow().isoformat(),
                "previous_version": current_version,
                "rotation_reason": "scheduled_rotation",
                "status": "active"
            })

            # Store new key version
            secret_data = {
                "key": new_master_key_b64,
                "metadata": new_metadata
            }

            response = self.client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret=secret_data,
                mount_point=self.config.mount_point
            )

            # Archive old version for decryption of existing data
            archive_path = f"tenants/{tenant_id}/archived-keys/{key_type}/v{current_version}"
            self.client.secrets.kv.v2.create_or_update_secret(
                path=archive_path,
                secret=current_response['data']['data'],
                mount_point=self.config.mount_point
            )

            # Update cache
            cache_key = f"{tenant_id}:{key_type}:master"
            self.key_cache[cache_key] = {
                "key": new_master_key,
                "metadata": new_metadata,
                "vault_version": response['data']['version'],
                "cached_at": time.time()
            }

            rotation_time = time.time() - start_time
            self.metrics["total_vault_time"] += rotation_time

            logger.info(f"Rotated master key for tenant {tenant_id} in {rotation_time*1000:.2f}ms")

            return {
                "key_id": f"{tenant_id}:{key_type}:master",
                "old_version": current_version,
                "new_version": response['data']['version'],
                "rotated_at": new_metadata["created_at"],
                "status": "active"
            }

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to rotate master key for tenant {tenant_id}: {str(e)}")
            raise

    def get_archived_key(self, tenant_id: UUID, key_type: str, version: int) -> bytes:
        """Retrieve archived key version for legacy data decryption."""
        start_time = time.time()

        try:
            archive_path = f"tenants/{tenant_id}/archived-keys/{key_type}/v{version}"

            response = self.client.secrets.kv.v2.read_secret_version(
                path=archive_path,
                mount_point=self.config.mount_point
            )

            if not response:
                raise ValueError(f"Archived key version {version} not found for tenant {tenant_id}")

            secret_data = response['data']['data']
            archived_key_b64 = secret_data["key"]
            archived_key = base64.b64decode(archived_key_b64)

            vault_time = time.time() - start_time
            self.metrics["key_retrievals"] += 1
            self.metrics["total_vault_time"] += vault_time

            logger.debug(f"Retrieved archived key v{version} for tenant {tenant_id}")
            return archived_key

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to retrieve archived key: {str(e)}")
            raise

    def create_data_encryption_key(self, tenant_id: UUID, purpose: str) -> dict[str, Any]:
        """Create data encryption key (DEK) derived from master key."""
        start_time = time.time()

        try:
            # Get master key
            master_key = self.get_master_key(tenant_id)

            # Generate DEK
            dek = AESGCM.generate_key(bit_length=256)

            # Encrypt DEK with master key
            aesgcm = AESGCM(master_key)
            nonce = os.urandom(12)
            encrypted_dek = aesgcm.encrypt(nonce, dek, None)

            # Store encrypted DEK
            dek_path = f"tenants/{tenant_id}/data-keys/{purpose}"

            dek_data = {
                "encrypted_key": base64.b64encode(encrypted_dek).decode('ascii'),
                "nonce": base64.b64encode(nonce).decode('ascii'),
                "purpose": purpose,
                "tenant_id": str(tenant_id),
                "created_at": datetime.utcnow().isoformat(),
                "algorithm": "AES-256-GCM",
                "master_key_version": self.key_cache[f"{tenant_id}:encryption:master"]["metadata"]["version"]
            }

            response = self.client.secrets.kv.v2.create_or_update_secret(
                path=dek_path,
                secret=dek_data,
                mount_point=self.config.mount_point
            )

            vault_time = time.time() - start_time
            self.metrics["key_creations"] += 1
            self.metrics["total_vault_time"] += vault_time

            logger.info(f"Created DEK for tenant {tenant_id} purpose {purpose}")

            return {
                "dek_id": f"{tenant_id}:{purpose}",
                "plaintext_key": dek,  # Return for immediate use
                "created_at": dek_data["created_at"],
                "version": response['data']['version']
            }

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to create DEK: {str(e)}")
            raise

    def get_data_encryption_key(self, tenant_id: UUID, purpose: str) -> bytes:
        """Retrieve and decrypt data encryption key."""
        start_time = time.time()

        try:
            # Retrieve encrypted DEK from Vault
            dek_path = f"tenants/{tenant_id}/data-keys/{purpose}"

            response = self.client.secrets.kv.v2.read_secret_version(
                path=dek_path,
                mount_point=self.config.mount_point
            )

            if not response:
                raise ValueError(f"DEK not found for tenant {tenant_id} purpose {purpose}")

            dek_data = response['data']['data']
            encrypted_dek = base64.b64decode(dek_data["encrypted_key"])
            nonce = base64.b64decode(dek_data["nonce"])

            # Get master key for decryption
            master_key = self.get_master_key(tenant_id)

            # Decrypt DEK
            aesgcm = AESGCM(master_key)
            dek = aesgcm.decrypt(nonce, encrypted_dek, None)

            vault_time = time.time() - start_time
            self.metrics["key_retrievals"] += 1
            self.metrics["total_vault_time"] += vault_time

            logger.debug(f"Retrieved DEK for tenant {tenant_id} purpose {purpose}")
            return dek

        except Exception as e:
            self.metrics["vault_errors"] += 1
            logger.error(f"Failed to retrieve DEK: {str(e)}")
            raise

    def list_tenant_keys(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """List all keys for a tenant."""
        try:
            keys = []

            # List master keys
            try:
                master_keys_path = f"tenants/{tenant_id}/master-keys"
                master_keys = self.client.secrets.kv.v2.list_secrets(
                    path=master_keys_path,
                    mount_point=self.config.mount_point
                )

                if master_keys and 'data' in master_keys and 'keys' in master_keys['data']:
                    for key_name in master_keys['data']['keys']:
                        keys.append({
                            "key_id": f"{tenant_id}:master:{key_name}",
                            "type": "master_key",
                            "purpose": key_name
                        })
            except VaultError:
                pass  # No master keys found

            # List data encryption keys
            try:
                dek_path = f"tenants/{tenant_id}/data-keys"
                dek_list = self.client.secrets.kv.v2.list_secrets(
                    path=dek_path,
                    mount_point=self.config.mount_point
                )

                if dek_list and 'data' in dek_list and 'keys' in dek_list['data']:
                    for key_name in dek_list['data']['keys']:
                        keys.append({
                            "key_id": f"{tenant_id}:dek:{key_name}",
                            "type": "data_encryption_key",
                            "purpose": key_name
                        })
            except VaultError:
                pass  # No DEKs found

            return keys

        except Exception as e:
            logger.error(f"Failed to list keys for tenant {tenant_id}: {str(e)}")
            raise

    def revoke_tenant_keys(self, tenant_id: UUID) -> bool:
        """Revoke all keys for a tenant (for tenant deletion)."""
        try:
            # Archive current keys before deletion
            tenant_keys = self.list_tenant_keys(tenant_id)

            for key_info in tenant_keys:
                # Move to revoked keys storage
                revoked_path = f"tenants/{tenant_id}/revoked-keys/{int(time.time())}"

                if key_info["type"] == "master_key":
                    original_path = f"tenants/{tenant_id}/master-keys/{key_info['purpose']}"
                else:
                    original_path = f"tenants/{tenant_id}/data-keys/{key_info['purpose']}"

                try:
                    # Get current key data
                    response = self.client.secrets.kv.v2.read_secret_version(
                        path=original_path,
                        mount_point=self.config.mount_point
                    )

                    if response:
                        # Add revocation metadata
                        revoked_data = response['data']['data'].copy()
                        revoked_data["revoked_at"] = datetime.utcnow().isoformat()
                        revoked_data["revocation_reason"] = "tenant_deletion"

                        # Store in revoked keys
                        self.client.secrets.kv.v2.create_or_update_secret(
                            path=revoked_path,
                            secret=revoked_data,
                            mount_point=self.config.mount_point
                        )

                        # Delete original key
                        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                            path=original_path,
                            mount_point=self.config.mount_point
                        )

                except VaultError as e:
                    logger.warning(f"Could not revoke key {key_info['key_id']}: {str(e)}")

            # Clear cache for tenant
            cache_keys_to_remove = [k for k in self.key_cache.keys() if str(tenant_id) in k]
            for cache_key in cache_keys_to_remove:
                del self.key_cache[cache_key]

            logger.info(f"Revoked all keys for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke keys for tenant {tenant_id}: {str(e)}")
            return False

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached key is still valid."""
        if cache_key not in self.key_cache:
            return False

        cached_at = self.key_cache[cache_key]["cached_at"]
        return (time.time() - cached_at) < self.cache_ttl

    def clear_cache(self):
        """Clear key cache."""
        self.key_cache.clear()
        logger.info("Cleared key cache")

    def get_key_management_metrics(self) -> dict[str, Any]:
        """Get key management performance metrics."""
        metrics = self.metrics.copy()

        if self.metrics["key_retrievals"] + self.metrics["key_creations"] > 0:
            metrics["avg_vault_operation_time"] = (
                self.metrics["total_vault_time"] /
                (self.metrics["key_retrievals"] + self.metrics["key_creations"])
            )

        metrics["cache_hit_rate"] = (
            self.metrics["cache_hits"] /
            max(self.metrics["cache_hits"] + self.metrics["cache_misses"], 1)
        )

        metrics["error_rate"] = (
            self.metrics["vault_errors"] /
            max(self.metrics["key_retrievals"] + self.metrics["key_creations"], 1)
        )

        metrics["cached_keys"] = len(self.key_cache)

        return metrics

    def health_check(self) -> dict[str, Any]:
        """Perform health check on Vault connectivity."""
        try:
            start_time = time.time()

            # Check authentication
            if not self.client.is_authenticated():
                return {
                    "status": "unhealthy",
                    "error": "Not authenticated with Vault",
                    "response_time_ms": 0
                }

            # Test read operation
            try:
                self.client.secrets.kv.v2.list_secrets(
                    path="health-check",
                    mount_point=self.config.mount_point
                )
            except VaultError:
                pass  # Expected if path doesn't exist

            response_time = (time.time() - start_time) * 1000

            return {
                "status": "healthy",
                "vault_url": self.config.url,
                "mount_point": self.config.mount_point,
                "response_time_ms": response_time,
                "cache_size": len(self.key_cache),
                "metrics": self.get_key_management_metrics()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": 0
            }
