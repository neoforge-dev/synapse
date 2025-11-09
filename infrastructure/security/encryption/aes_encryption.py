"""AES-256-GCM Encryption with field-level encryption capabilities."""

import base64
import hashlib
import logging
import os
import time
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass


class AESGCMEncryption:
    """High-performance AES-256-GCM encryption for data at rest."""

    def __init__(self, key: bytes | None = None):
        """Initialize with optional key (generates if not provided)."""
        self.key = key or AESGCM.generate_key(bit_length=256)
        self.aesgcm = AESGCM(self.key)
        self.performance_metrics = {
            "encrypt_ops": 0,
            "decrypt_ops": 0,
            "total_encrypt_time": 0.0,
            "total_decrypt_time": 0.0,
            "avg_encrypt_time": 0.0,
            "avg_decrypt_time": 0.0
        }

    def encrypt(self, plaintext: str | bytes, associated_data: bytes | None = None) -> dict[str, str]:
        """Encrypt data with AES-256-GCM and return nonce + ciphertext."""
        start_time = time.time()

        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')

            # Generate random nonce (96 bits for GCM)
            nonce = os.urandom(12)

            # Encrypt with AEAD
            ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data)

            # Update performance metrics
            encrypt_time = time.time() - start_time
            self._update_encrypt_metrics(encrypt_time)

            return {
                "nonce": base64.b64encode(nonce).decode('ascii'),
                "ciphertext": base64.b64encode(ciphertext).decode('ascii'),
                "algorithm": "AES-256-GCM"
            }

        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}") from e

    def decrypt(self, encrypted_data: dict[str, str], associated_data: bytes | None = None) -> bytes:
        """Decrypt AES-256-GCM encrypted data."""
        start_time = time.time()

        try:
            nonce = base64.b64decode(encrypted_data["nonce"])
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])

            # Decrypt with AEAD verification
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, associated_data)

            # Update performance metrics
            decrypt_time = time.time() - start_time
            self._update_decrypt_metrics(decrypt_time)

            return plaintext

        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}") from e

    def _update_encrypt_metrics(self, operation_time: float):
        """Update encryption performance metrics."""
        self.performance_metrics["encrypt_ops"] += 1
        self.performance_metrics["total_encrypt_time"] += operation_time
        self.performance_metrics["avg_encrypt_time"] = (
            self.performance_metrics["total_encrypt_time"] /
            self.performance_metrics["encrypt_ops"]
        )

    def _update_decrypt_metrics(self, operation_time: float):
        """Update decryption performance metrics."""
        self.performance_metrics["decrypt_ops"] += 1
        self.performance_metrics["total_decrypt_time"] += operation_time
        self.performance_metrics["avg_decrypt_time"] = (
            self.performance_metrics["total_decrypt_time"] /
            self.performance_metrics["decrypt_ops"]
        )

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get encryption performance metrics."""
        return self.performance_metrics.copy()

    @classmethod
    def derive_key_from_password(cls, password: str, salt: bytes) -> bytes:
        """Derive AES key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode('utf-8'))


class FieldLevelEncryption:
    """Field-level encryption for sensitive data with tenant isolation."""

    # Define sensitive fields that require encryption
    SENSITIVE_FIELDS = {
        'pii': ['email', 'phone', 'ssn', 'name', 'address', 'birth_date'],
        'financial': ['account_number', 'routing_number', 'credit_card', 'salary'],
        'medical': ['diagnosis', 'treatment', 'medical_record', 'health_data'],
        'business': ['api_key', 'secret', 'token', 'password']
    }

    def __init__(self, tenant_id: UUID, master_key: bytes):
        """Initialize with tenant-specific encryption key."""
        self.tenant_id = tenant_id
        # Derive tenant-specific key from master key
        self.tenant_key = self._derive_tenant_key(master_key, tenant_id)
        self.encryptor = AESGCMEncryption(self.tenant_key)

    def _derive_tenant_key(self, master_key: bytes, tenant_id: UUID) -> bytes:
        """Derive tenant-specific key for isolation."""
        tenant_salt = hashlib.sha256(str(tenant_id).encode()).digest()[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_salt,
            iterations=10000,
        )
        return kdf.derive(master_key)

    def encrypt_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive fields in document."""
        encrypted_doc = document.copy()

        # Track which fields were encrypted
        encrypted_fields = []

        for category, fields in self.SENSITIVE_FIELDS.items():
            for field in fields:
                if field in document:
                    # Create associated data for field integrity
                    associated_data = f"{self.tenant_id}:{field}".encode()

                    # Encrypt field value
                    field_value = str(document[field])
                    encrypted_data = self.encryptor.encrypt(field_value, associated_data)

                    # Store encrypted data with metadata
                    encrypted_doc[field] = {
                        "encrypted": True,
                        "category": category,
                        "data": encrypted_data
                    }
                    encrypted_fields.append(field)

        # Add encryption metadata
        encrypted_doc["_encryption_metadata"] = {
            "tenant_id": str(self.tenant_id),
            "encrypted_fields": encrypted_fields,
            "encryption_timestamp": time.time(),
            "version": "1.0"
        }

        logger.info(f"Encrypted {len(encrypted_fields)} fields for tenant {self.tenant_id}")
        return encrypted_doc

    def decrypt_document(self, encrypted_doc: dict[str, Any]) -> dict[str, Any]:
        """Decrypt sensitive fields in document."""
        if "_encryption_metadata" not in encrypted_doc:
            return encrypted_doc  # Not encrypted

        metadata = encrypted_doc["_encryption_metadata"]

        # Validate tenant access
        if metadata["tenant_id"] != str(self.tenant_id):
            raise EncryptionError("Access denied: document encrypted for different tenant")

        decrypted_doc = encrypted_doc.copy()

        for field in metadata["encrypted_fields"]:
            if field in encrypted_doc and isinstance(encrypted_doc[field], dict):
                field_data = encrypted_doc[field]

                if field_data.get("encrypted"):
                    # Create associated data for verification
                    associated_data = f"{self.tenant_id}:{field}".encode()

                    # Decrypt field value
                    decrypted_bytes = self.encryptor.decrypt(
                        field_data["data"],
                        associated_data
                    )
                    decrypted_doc[field] = decrypted_bytes.decode('utf-8')

        # Remove encryption metadata from final document
        del decrypted_doc["_encryption_metadata"]

        logger.info(f"Decrypted {len(metadata['encrypted_fields'])} fields for tenant {self.tenant_id}")
        return decrypted_doc

    def is_field_encrypted(self, document: dict[str, Any], field_name: str) -> bool:
        """Check if a specific field is encrypted."""
        if "_encryption_metadata" not in document:
            return False
        return field_name in document["_encryption_metadata"]["encrypted_fields"]

    def get_encrypted_fields_summary(self, document: dict[str, Any]) -> dict[str, Any]:
        """Get summary of encrypted fields in document."""
        if "_encryption_metadata" not in document:
            return {"encrypted": False}

        metadata = document["_encryption_metadata"]
        field_categories = {}

        for field in metadata["encrypted_fields"]:
            if field in document and isinstance(document[field], dict):
                category = document[field].get("category", "unknown")
                if category not in field_categories:
                    field_categories[category] = []
                field_categories[category].append(field)

        return {
            "encrypted": True,
            "tenant_id": metadata["tenant_id"],
            "total_encrypted_fields": len(metadata["encrypted_fields"]),
            "field_categories": field_categories,
            "encryption_timestamp": metadata["encryption_timestamp"]
        }


class SearchableEncryption:
    """Searchable encryption for encrypted data queries."""

    def __init__(self, tenant_key: bytes):
        """Initialize with tenant-specific key."""
        self.tenant_key = tenant_key

    def create_search_index(self, plaintext: str) -> list[str]:
        """Create searchable index tokens from plaintext."""
        # Tokenize and create encrypted searchable tokens
        words = plaintext.lower().split()
        tokens = []

        for word in words:
            if len(word) >= 3:  # Only index words of 3+ characters
                # Create deterministic encrypted token for searching
                token_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    word.encode('utf-8'),
                    self.tenant_key,
                    10000
                )
                tokens.append(base64.b64encode(token_hash).decode('ascii'))

        return tokens

    def create_search_token(self, search_term: str) -> str:
        """Create search token from search term."""
        search_term = search_term.lower()
        token_hash = hashlib.pbkdf2_hmac(
            'sha256',
            search_term.encode('utf-8'),
            self.tenant_key,
            10000
        )
        return base64.b64encode(token_hash).decode('ascii')

    def can_search_encrypted_field(self, encrypted_document: dict[str, Any],
                                  field_name: str, search_term: str) -> bool:
        """Check if search term matches encrypted field (without decryption)."""
        if not self._has_search_index(encrypted_document, field_name):
            return False

        search_token = self.create_search_token(search_term)
        field_tokens = encrypted_document[field_name].get("search_tokens", [])

        return search_token in field_tokens

    def _has_search_index(self, document: dict[str, Any], field_name: str) -> bool:
        """Check if field has searchable index."""
        if field_name not in document:
            return False

        field_data = document[field_name]
        if not isinstance(field_data, dict) or not field_data.get("encrypted"):
            return False

        return "search_tokens" in field_data
