"""Central data encryption manager coordinating all encryption operations."""

import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta

from .aes_encryption import AESGCMEncryption, FieldLevelEncryption, SearchableEncryption
from .client_encryption import ClientSideEncryption, EndToEndEncryption
from .performance_monitor import EncryptionPerformanceMonitor

logger = logging.getLogger(__name__)


class EncryptionPolicy:
    """Define encryption policies for different data types and compliance requirements."""
    
    POLICIES = {
        "hipaa": {
            "required_fields": ["medical_record", "diagnosis", "treatment", "patient_id"],
            "encryption_level": "field_level",
            "key_rotation_days": 30,
            "audit_required": True
        },
        "pci_dss": {
            "required_fields": ["credit_card", "account_number", "cvv", "expiry"],
            "encryption_level": "field_level", 
            "key_rotation_days": 90,
            "audit_required": True
        },
        "gdpr": {
            "required_fields": ["email", "name", "phone", "address", "ip_address"],
            "encryption_level": "field_level",
            "key_rotation_days": 365,
            "audit_required": True
        },
        "sox": {
            "required_fields": ["financial_data", "audit_trail", "transaction"],
            "encryption_level": "document_level",
            "key_rotation_days": 90,
            "audit_required": True
        },
        "enterprise": {
            "required_fields": ["api_key", "secret", "token", "password"],
            "encryption_level": "field_level",
            "key_rotation_days": 30,
            "audit_required": True
        }
    }
    
    @classmethod
    def get_policy_for_document(cls, document: Dict[str, Any]) -> Optional[str]:
        """Determine which encryption policy applies to document."""
        document_fields = set(document.keys())
        
        for policy_name, policy in cls.POLICIES.items():
            required_fields = set(policy["required_fields"])
            if required_fields.intersection(document_fields):
                return policy_name
        
        return "enterprise"  # Default policy
    
    @classmethod
    def should_encrypt_field(cls, field_name: str, policy_name: str) -> bool:
        """Check if field should be encrypted according to policy."""
        if policy_name not in cls.POLICIES:
            return False
        
        policy = cls.POLICIES[policy_name]
        return field_name in policy["required_fields"]


class DataEncryptionManager:
    """Central manager for all data encryption operations in zero-trust architecture."""
    
    def __init__(self, master_key: bytes, tenant_id: UUID):
        """Initialize encryption manager with master key and tenant context."""
        self.master_key = master_key
        self.tenant_id = tenant_id
        
        # Initialize encryption components
        self.aes_encryption = AESGCMEncryption()
        self.field_encryption = FieldLevelEncryption(tenant_id, master_key)
        self.client_encryption = ClientSideEncryption()
        self.e2e_encryption = EndToEndEncryption(tenant_id)
        self.searchable_encryption = SearchableEncryption(
            self.field_encryption.tenant_key
        )
        
        # Performance monitoring
        self.performance_monitor = EncryptionPerformanceMonitor()
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized DataEncryptionManager for tenant {tenant_id}")
    
    def encrypt_document(self, document: Dict[str, Any], 
                        encryption_mode: str = "auto",
                        client_id: Optional[str] = None,
                        server_public_key: Optional[bytes] = None) -> Dict[str, Any]:
        """Encrypt document based on policy and mode."""
        start_time = time.time()
        
        try:
            # Determine encryption policy
            policy_name = EncryptionPolicy.get_policy_for_document(document)
            
            # Log encryption attempt
            self._audit_log("encrypt_start", {
                "document_id": document.get("id", "unknown"),
                "policy": policy_name,
                "mode": encryption_mode,
                "fields_count": len(document)
            })
            
            encrypted_doc = None
            
            if encryption_mode == "field_level":
                encrypted_doc = self._encrypt_field_level(document, policy_name)
            elif encryption_mode == "document_level":
                encrypted_doc = self._encrypt_document_level(document)
            elif encryption_mode == "end_to_end" and client_id and server_public_key:
                encrypted_doc = self._encrypt_end_to_end(document, client_id, server_public_key)
            elif encryption_mode == "auto":
                encrypted_doc = self._encrypt_auto_mode(document, policy_name, client_id, server_public_key)
            else:
                raise ValueError(f"Invalid encryption mode: {encryption_mode}")
            
            # Record performance metrics
            encryption_time = time.time() - start_time
            self.performance_monitor.record_encryption(encryption_time, len(str(document)))
            
            # Log successful encryption
            self._audit_log("encrypt_success", {
                "document_id": encrypted_doc.get("id", "unknown"),
                "encryption_time": encryption_time,
                "size_bytes": len(str(encrypted_doc))
            })
            
            return encrypted_doc
            
        except Exception as e:
            encryption_time = time.time() - start_time
            self._audit_log("encrypt_error", {
                "document_id": document.get("id", "unknown"),
                "error": str(e),
                "encryption_time": encryption_time
            })
            logger.error(f"Document encryption failed: {str(e)}")
            raise
    
    def decrypt_document(self, encrypted_doc: Dict[str, Any],
                        client_id: Optional[str] = None) -> Dict[str, Any]:
        """Decrypt document based on encryption type."""
        start_time = time.time()
        
        try:
            # Determine encryption type
            encryption_type = self._detect_encryption_type(encrypted_doc)
            
            self._audit_log("decrypt_start", {
                "document_id": encrypted_doc.get("id", "unknown"),
                "encryption_type": encryption_type
            })
            
            decrypted_doc = None
            
            if encryption_type == "field_level":
                decrypted_doc = self.field_encryption.decrypt_document(encrypted_doc)
            elif encryption_type == "document_level":
                decrypted_doc = self._decrypt_document_level(encrypted_doc)
            elif encryption_type == "end_to_end" and client_id:
                decrypted_doc = self.e2e_encryption.decrypt_document_e2e(encrypted_doc, client_id)
            else:
                raise ValueError(f"Cannot decrypt document with type: {encryption_type}")
            
            # Record performance metrics
            decryption_time = time.time() - start_time
            self.performance_monitor.record_decryption(decryption_time, len(str(encrypted_doc)))
            
            # Log successful decryption
            self._audit_log("decrypt_success", {
                "document_id": decrypted_doc.get("id", "unknown"),
                "decryption_time": decryption_time
            })
            
            return decrypted_doc
            
        except Exception as e:
            decryption_time = time.time() - start_time
            self._audit_log("decrypt_error", {
                "document_id": encrypted_doc.get("id", "unknown"),
                "error": str(e),
                "decryption_time": decryption_time
            })
            logger.error(f"Document decryption failed: {str(e)}")
            raise
    
    def search_encrypted_documents(self, search_query: str, 
                                 encrypted_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Search through encrypted documents without full decryption."""
        start_time = time.time()
        
        try:
            search_results = []
            search_token = self.searchable_encryption.create_search_token(search_query)
            
            for doc in encrypted_documents:
                if self._can_search_document(doc, search_token):
                    search_results.append(doc)
            
            # Record search performance
            search_time = time.time() - start_time
            self.performance_monitor.record_search(search_time, len(encrypted_documents), len(search_results))
            
            self._audit_log("search_encrypted", {
                "query": search_query,
                "documents_searched": len(encrypted_documents),
                "results_found": len(search_results),
                "search_time": search_time
            })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Encrypted search failed: {str(e)}")
            raise
    
    def _encrypt_field_level(self, document: Dict[str, Any], policy_name: str) -> Dict[str, Any]:
        """Encrypt at field level based on policy."""
        encrypted_doc = self.field_encryption.encrypt_document(document)
        
        # Add searchable tokens for encrypted fields
        for field_name, field_data in encrypted_doc.items():
            if isinstance(field_data, dict) and field_data.get("encrypted"):
                # Get original field value for creating search tokens
                original_value = document.get(field_name, "")
                if isinstance(original_value, str):
                    search_tokens = self.searchable_encryption.create_search_index(original_value)
                    field_data["search_tokens"] = search_tokens
        
        return encrypted_doc
    
    def _encrypt_document_level(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt entire document."""
        document_json = str(document)
        encrypted_data = self.aes_encryption.encrypt(document_json)
        
        return {
            "id": document.get("id", f"doc_{int(time.time())}"),
            "tenant_id": str(self.tenant_id),
            "encryption_type": "document_level",
            "encrypted_data": encrypted_data,
            "created_timestamp": time.time()
        }
    
    def _encrypt_end_to_end(self, document: Dict[str, Any], client_id: str, 
                          server_public_key: bytes) -> Dict[str, Any]:
        """Encrypt with end-to-end encryption."""
        return self.e2e_encryption.encrypt_document_e2e(document, client_id, server_public_key)
    
    def _encrypt_auto_mode(self, document: Dict[str, Any], policy_name: str,
                          client_id: Optional[str], server_public_key: Optional[bytes]) -> Dict[str, Any]:
        """Auto-select encryption mode based on policy and available resources."""
        if client_id and server_public_key:
            # Use E2E if client context available
            return self._encrypt_end_to_end(document, client_id, server_public_key)
        elif policy_name in ["hipaa", "pci_dss", "gdpr"]:
            # Use field-level for compliance policies
            return self._encrypt_field_level(document, policy_name)
        else:
            # Default to document-level encryption
            return self._encrypt_document_level(document)
    
    def _decrypt_document_level(self, encrypted_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt document-level encrypted data."""
        encrypted_data = encrypted_doc["encrypted_data"]
        decrypted_bytes = self.aes_encryption.decrypt(encrypted_data)
        
        # Parse decrypted JSON back to dictionary
        import json
        return json.loads(decrypted_bytes.decode('utf-8'))
    
    def _detect_encryption_type(self, encrypted_doc: Dict[str, Any]) -> str:
        """Detect the encryption type of a document."""
        if "_encryption_metadata" in encrypted_doc:
            return "field_level"
        elif "encryption_type" in encrypted_doc:
            return encrypted_doc["encryption_type"]
        else:
            return "unknown"
    
    def _can_search_document(self, document: Dict[str, Any], search_token: str) -> bool:
        """Check if document matches search without full decryption."""
        if "_encryption_metadata" not in document:
            return False
        
        # Check searchable tokens in encrypted fields
        for field_name, field_data in document.items():
            if isinstance(field_data, dict) and field_data.get("encrypted"):
                search_tokens = field_data.get("search_tokens", [])
                if search_token in search_tokens:
                    return True
        
        return False
    
    def _audit_log(self, event_type: str, details: Dict[str, Any]):
        """Log encryption operations for audit purposes."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": str(self.tenant_id),
            "event_type": event_type,
            "details": details
        }
        self.audit_log.append(audit_entry)
        
        # Keep audit log size manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]  # Keep last 5000 entries
    
    def get_encryption_health_status(self) -> Dict[str, Any]:
        """Get comprehensive encryption system health status."""
        performance_stats = self.performance_monitor.get_performance_statistics()
        
        return {
            "tenant_id": str(self.tenant_id),
            "encryption_components": {
                "aes_encryption": "active",
                "field_encryption": "active", 
                "client_encryption": "active",
                "searchable_encryption": "active"
            },
            "performance_metrics": performance_stats,
            "audit_log_entries": len(self.audit_log),
            "last_encryption_time": performance_stats.get("last_encryption_time"),
            "average_encryption_overhead_ms": performance_stats.get("avg_encryption_time_ms", 0) * 1000,
            "compliance_policies_active": list(EncryptionPolicy.POLICIES.keys()),
            "health_status": "healthy" if performance_stats.get("avg_encryption_time_ms", 0) < 0.005 else "degraded"
        }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:] if self.audit_log else []