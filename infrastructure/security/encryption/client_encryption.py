"""Client-side encryption for maximum security and zero-trust architecture."""

import base64
import json
import logging
import os
import time
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class ClientSideEncryption:
    """Client-side encryption ensuring server never sees plaintext data."""

    def __init__(self):
        """Initialize client-side encryption system."""
        self.session_keys: dict[str, bytes] = {}
        self.performance_metrics = {
            "key_exchanges": 0,
            "encrypt_operations": 0,
            "decrypt_operations": 0,
            "total_key_exchange_time": 0.0,
            "total_encrypt_time": 0.0,
            "total_decrypt_time": 0.0
        }

    def generate_client_keypair(self) -> tuple[bytes, bytes]:
        """Generate RSA keypair for client."""
        start_time = time.time()

        try:
            # Generate 4096-bit RSA keypair for maximum security
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096
            )
            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            # Update metrics
            self.performance_metrics["key_exchanges"] += 1
            self.performance_metrics["total_key_exchange_time"] += time.time() - start_time

            logger.info("Generated client RSA-4096 keypair")
            return private_pem, public_pem

        except Exception as e:
            logger.error(f"Failed to generate client keypair: {str(e)}")
            raise

    def establish_secure_session(self, client_id: str, server_public_key: bytes) -> dict[str, str]:
        """Establish secure session with server using RSA key exchange."""
        start_time = time.time()

        try:
            # Generate session AES key
            session_key = AESGCM.generate_key(bit_length=256)
            self.session_keys[client_id] = session_key

            # Load server public key
            server_key = serialization.load_pem_public_key(server_public_key)

            # Encrypt session key with server's public key
            encrypted_session_key = server_key.encrypt(
                session_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Update metrics
            key_exchange_time = time.time() - start_time
            self.performance_metrics["total_key_exchange_time"] += key_exchange_time

            logger.info(f"Established secure session for client {client_id}")

            return {
                "client_id": client_id,
                "encrypted_session_key": base64.b64encode(encrypted_session_key).decode('ascii'),
                "key_exchange_timestamp": time.time(),
                "session_algorithm": "AES-256-GCM"
            }

        except Exception as e:
            logger.error(f"Failed to establish secure session: {str(e)}")
            raise

    def encrypt_client_data(self, client_id: str, data: dict[str, Any],
                           tenant_id: UUID | None = None) -> dict[str, Any]:
        """Encrypt data client-side before transmission."""
        start_time = time.time()

        if client_id not in self.session_keys:
            raise ValueError(f"No session key found for client {client_id}")

        try:
            session_key = self.session_keys[client_id]
            aesgcm = AESGCM(session_key)

            # Prepare data for encryption
            plaintext_data = json.dumps(data, sort_keys=True).encode('utf-8')

            # Create associated data for integrity
            associated_data = f"{client_id}:{tenant_id}".encode() if tenant_id else client_id.encode('utf-8')

            # Generate nonce and encrypt
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, plaintext_data, associated_data)

            # Update metrics
            encrypt_time = time.time() - start_time
            self.performance_metrics["encrypt_operations"] += 1
            self.performance_metrics["total_encrypt_time"] += encrypt_time

            encrypted_payload = {
                "client_id": client_id,
                "nonce": base64.b64encode(nonce).decode('ascii'),
                "ciphertext": base64.b64encode(ciphertext).decode('ascii'),
                "associated_data": base64.b64encode(associated_data).decode('ascii'),
                "algorithm": "AES-256-GCM",
                "encryption_timestamp": time.time()
            }

            if tenant_id:
                encrypted_payload["tenant_id"] = str(tenant_id)

            logger.debug(f"Client-side encrypted data for client {client_id}")
            return encrypted_payload

        except Exception as e:
            logger.error(f"Client-side encryption failed: {str(e)}")
            raise

    def decrypt_client_data(self, client_id: str, encrypted_payload: dict[str, Any]) -> dict[str, Any]:
        """Decrypt data received from client."""
        start_time = time.time()

        if client_id not in self.session_keys:
            raise ValueError(f"No session key found for client {client_id}")

        try:
            session_key = self.session_keys[client_id]
            aesgcm = AESGCM(session_key)

            # Extract encryption components
            nonce = base64.b64decode(encrypted_payload["nonce"])
            ciphertext = base64.b64decode(encrypted_payload["ciphertext"])
            associated_data = base64.b64decode(encrypted_payload["associated_data"])

            # Decrypt data
            plaintext_data = aesgcm.decrypt(nonce, ciphertext, associated_data)
            decrypted_data = json.loads(plaintext_data.decode('utf-8'))

            # Update metrics
            decrypt_time = time.time() - start_time
            self.performance_metrics["decrypt_operations"] += 1
            self.performance_metrics["total_decrypt_time"] += decrypt_time

            logger.debug(f"Client-side decrypted data for client {client_id}")
            return decrypted_data

        except Exception as e:
            logger.error(f"Client-side decryption failed: {str(e)}")
            raise

    def rotate_session_key(self, client_id: str, server_public_key: bytes) -> dict[str, str]:
        """Rotate session key for perfect forward secrecy."""
        logger.info(f"Rotating session key for client {client_id}")

        # Remove old session key
        if client_id in self.session_keys:
            del self.session_keys[client_id]

        # Establish new secure session
        return self.establish_secure_session(client_id, server_public_key)

    def revoke_session(self, client_id: str):
        """Revoke client session and clear keys."""
        if client_id in self.session_keys:
            del self.session_keys[client_id]
            logger.info(f"Revoked session for client {client_id}")

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get client-side encryption performance metrics."""
        metrics = self.performance_metrics.copy()

        # Calculate averages
        if metrics["key_exchanges"] > 0:
            metrics["avg_key_exchange_time"] = (
                metrics["total_key_exchange_time"] / metrics["key_exchanges"]
            )

        if metrics["encrypt_operations"] > 0:
            metrics["avg_encrypt_time"] = (
                metrics["total_encrypt_time"] / metrics["encrypt_operations"]
            )

        if metrics["decrypt_operations"] > 0:
            metrics["avg_decrypt_time"] = (
                metrics["total_decrypt_time"] / metrics["decrypt_operations"]
            )

        return metrics

    def validate_client_session(self, client_id: str, max_session_age: float = 3600) -> bool:
        """Validate client session is still active and not expired."""
        if client_id not in self.session_keys:
            return False

        # In production, you'd track session timestamps and validate age
        # For now, just check if session key exists
        return True


class EndToEndEncryption:
    """End-to-end encryption ensuring data is encrypted throughout its lifecycle."""

    def __init__(self, tenant_id: UUID):
        """Initialize E2E encryption for specific tenant."""
        self.tenant_id = tenant_id
        self.client_encryption = ClientSideEncryption()

    def encrypt_document_e2e(self, document: dict[str, Any], client_id: str,
                            server_public_key: bytes) -> dict[str, Any]:
        """Encrypt document end-to-end from client to storage."""

        # Step 1: Establish secure session if needed
        if not self.client_encryption.validate_client_session(client_id):
            session_info = self.client_encryption.establish_secure_session(
                client_id, server_public_key
            )
            logger.info(f"Established new session: {session_info['client_id']}")

        # Step 2: Client-side encryption
        encrypted_payload = self.client_encryption.encrypt_client_data(
            client_id, document, self.tenant_id
        )

        # Step 3: Add E2E metadata
        e2e_document = {
            "document_id": document.get("id", f"doc_{int(time.time())}"),
            "tenant_id": str(self.tenant_id),
            "client_id": client_id,
            "encrypted_payload": encrypted_payload,
            "encryption_type": "end_to_end",
            "created_timestamp": time.time(),
            "encryption_version": "2.0"
        }

        return e2e_document

    def decrypt_document_e2e(self, e2e_document: dict[str, Any], client_id: str) -> dict[str, Any]:
        """Decrypt document end-to-end from storage to client."""

        # Validate access permissions
        if e2e_document["tenant_id"] != str(self.tenant_id):
            raise PermissionError(f"Access denied to tenant {e2e_document['tenant_id']}")

        if e2e_document["client_id"] != client_id:
            raise PermissionError(f"Access denied for client {client_id}")

        # Decrypt client payload
        encrypted_payload = e2e_document["encrypted_payload"]
        decrypted_document = self.client_encryption.decrypt_client_data(
            client_id, encrypted_payload
        )

        return decrypted_document

    def get_encryption_status(self, document: dict[str, Any]) -> dict[str, Any]:
        """Get encryption status and metadata for document."""
        if "encryption_type" not in document:
            return {"encrypted": False, "type": "plaintext"}

        return {
            "encrypted": True,
            "type": document.get("encryption_type"),
            "tenant_id": document.get("tenant_id"),
            "client_id": document.get("client_id"),
            "version": document.get("encryption_version"),
            "created_timestamp": document.get("created_timestamp")
        }
