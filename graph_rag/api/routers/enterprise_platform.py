#!/usr/bin/env python3
"""
Epic 15 Phase 2: Enterprise Platform Consolidated Router
Mission: Consolidate auth, enterprise_auth, compliance, admin systems
Enterprise Readiness: Multi-tenant, SSO, RBAC, GDPR/SOC2/HIPAA compliance

This router consolidates:
- Authentication (from auth.py)
- Enterprise authentication (from enterprise_auth.py)
- Compliance management (from compliance.py)
- Admin system management (from admin.py)
"""

import logging
import time
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# Auth and security imports
from graph_rag.api.auth.dependencies import (
    get_auth_provider,
    get_current_user,
    get_current_user_optional,
    get_jwt_handler,
    require_admin_role,
)
from graph_rag.api.auth.enterprise_models import (
    AuditEventType,
    ComplianceFramework,
    ComplianceReportRequest,
    LDAPAuthRequest,
    LDAPConfiguration,
    MFAChallengeRequest,
    MFAType,
    OAuthAuthRequest,
    OAuthConfiguration,
    SAMLAuthRequest,
    SAMLConfiguration,
    TenantCreateRequest,
)
from graph_rag.api.auth.enterprise_providers import EnterpriseAuthProvider
from graph_rag.api.auth.jwt_handler import JWTHandler
from graph_rag.api.auth.models import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    TokenResponse,
    User,
    UserCreate,
    UserLogin,
)
from graph_rag.api.auth.providers import AuthProvider

# System management imports
from graph_rag.api.dependencies import (
    get_graph_repository,
    get_llm,
    get_vector_store,
)
from graph_rag.api.health import (
    HealthChecker,
    SystemHealth,
    check_embedding_service,
    check_graph_repository,
    check_llm_service,
    check_vector_store,
)
from graph_rag.api.performance_optimization import (
    get_advanced_performance_stats,
    get_optimization_recommendations,
    get_performance_monitor,
    get_query_optimizer,
)
from graph_rag.api.system_metrics import (
    assess_system_health,
    get_application_metrics,
    get_platform_info,
    get_system_metrics,
)
from graph_rag.core.interfaces import GraphRepository, VectorStore
from graph_rag.llm.protocols import LLMService
from graph_rag.observability import (
    ComponentType,
    LogContext,
    get_component_logger,
)
from graph_rag.services.maintenance import IntegrityCheckJob

# Compliance imports
try:
    from graph_rag.compliance.gdpr_processor import gdpr_processor
    from graph_rag.compliance.hipaa_controls import HIPAAComplianceStatus, hipaa_framework
    from graph_rag.compliance.soc2_controls import ControlStatus, soc2_framework
except ImportError:
    # Mock compliance imports if modules don't exist
    gdpr_processor = None
    hipaa_framework = None
    soc2_framework = None
    ControlStatus = None
    HIPAAComplianceStatus = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
admin_logger = get_component_logger(ComponentType.API, "admin")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_enterprise_platform_router() -> APIRouter:
    """Factory function to create the consolidated enterprise platform router."""
    router = APIRouter()

    # ===============================
    # CORE AUTHENTICATION ENDPOINTS
    # ===============================

    @router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
    async def register_user(
        user_data: UserCreate,
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Register a new user account."""
        try:
            # Create the user
            user = await auth_provider.create_user(user_data)

            # Generate access token
            access_token = jwt_handler.create_access_token(user)

            # Update last login
            await auth_provider.update_last_login(user.id)

            logger.info(f"User registered successfully: {user.username}")

            return TokenResponse(
                access_token=access_token,
                expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"User registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )

    @router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
    async def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Authenticate user and return access token."""
        user = await auth_provider.authenticate_user(
            form_data.username,
            form_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        access_token = jwt_handler.create_access_token(user)

        # Update last login
        await auth_provider.update_last_login(user.id)

        logger.info(f"User logged in: {user.username}")

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
            user=user
        )

    @router.post("/auth/login/json", response_model=TokenResponse, tags=["Authentication"])
    async def login_user_json(
        login_data: UserLogin,
        auth_provider: AuthProvider = Depends(get_auth_provider),
        jwt_handler: JWTHandler = Depends(get_jwt_handler)
    ) -> TokenResponse:
        """Authenticate user with JSON payload and return access token."""
        user = await auth_provider.authenticate_user(
            login_data.username,
            login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        access_token = jwt_handler.create_access_token(user)

        # Update last login
        await auth_provider.update_last_login(user.id)

        logger.info(f"User logged in via JSON: {user.username}")

        return TokenResponse(
            access_token=access_token,
            expires_in=jwt_handler.settings.access_token_expire_minutes * 60,
            user=user
        )

    @router.get("/auth/me", response_model=User, tags=["Authentication"])
    async def get_current_user_info(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """Get current user information."""
        return current_user

    @router.post("/auth/api-keys", response_model=APIKeyResponse, tags=["Authentication"])
    async def create_api_key(
        key_data: APIKeyCreate,
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> APIKeyResponse:
        """Create a new API key for the current user."""
        try:
            api_key_model, actual_key = await auth_provider.create_api_key(
                current_user.id,
                key_data
            )

            logger.info(f"API key created: {key_data.name} for user {current_user.username}")

            return APIKeyResponse(
                id=api_key_model.id,
                name=api_key_model.name,
                description=api_key_model.description,
                api_key=actual_key,  # Only shown here, never again
                expires_at=api_key_model.expires_at
            )

        except Exception as e:
            logger.error(f"API key creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )

    @router.get("/auth/api-keys", response_model=list[APIKey], tags=["Authentication"])
    async def list_api_keys(
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> list[APIKey]:
        """List all API keys for the current user."""
        if hasattr(auth_provider, 'list_user_api_keys'):
            return await auth_provider.list_user_api_keys(current_user.id)
        else:
            # Fallback for providers that don't implement this method
            return []

    @router.delete("/auth/api-keys/{key_id}", tags=["Authentication"])
    async def revoke_api_key(
        key_id: UUID,
        current_user: User = Depends(get_current_user),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> dict:
        """Revoke an API key."""
        success = await auth_provider.revoke_api_key(current_user.id, key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        logger.info(f"API key {key_id} revoked by user {current_user.username}")
        return {"message": "API key revoked successfully"}

    # Admin-only endpoints
    @router.post("/auth/admin/users", response_model=User, tags=["Authentication"])
    async def create_user_admin(
        user_data: UserCreate,
        _admin: User = Depends(require_admin_role),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> User:
        """Admin endpoint to create users."""
        try:
            user = await auth_provider.create_user(user_data)
            logger.info(f"Admin created user: {user.username}")
            return user
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @router.get("/auth/admin/users/{user_id}", response_model=User, tags=["Authentication"])
    async def get_user_admin(
        user_id: UUID,
        _admin: User = Depends(require_admin_role),
        auth_provider: AuthProvider = Depends(get_auth_provider)
    ) -> User:
        """Admin endpoint to get user by ID."""
        user = await auth_provider.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    # ===============================
    # ENTERPRISE AUTHENTICATION ENDPOINTS
    # ===============================

    @router.post("/auth/enterprise/tenants", status_code=status.HTTP_201_CREATED, tags=["Enterprise Authentication"])
    async def create_tenant(
        tenant_data: TenantCreateRequest,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Create a new enterprise tenant."""
        try:
            tenant = await auth_provider.create_tenant(tenant_data)
            
            # Log audit event
            await auth_provider.log_audit_event(
                tenant_id=tenant.id,
                event_type=AuditEventType.TENANT_CREATED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="create_tenant",
                result="success",
                details={
                    "tenant_name": tenant.name,
                    "domain": tenant.domain,
                    "compliance_frameworks": [f.value for f in tenant.compliance_frameworks]
                }
            )
            
            return {
                "tenant_id": tenant.id,
                "name": tenant.name,
                "domain": tenant.domain,
                "subdomain": tenant.subdomain,
                "compliance_frameworks": tenant.compliance_frameworks,
                "created_at": tenant.created_at
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Tenant creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )

    @router.get("/auth/enterprise/tenants/{tenant_id}", tags=["Enterprise Authentication"])
    async def get_tenant(
        tenant_id: UUID,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Get tenant information."""
        tenant = await auth_provider.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        return tenant

    # --- SAML 2.0 Endpoints ---
    @router.post("/auth/enterprise/saml/configure", tags=["Enterprise Authentication"])
    async def configure_saml(
        saml_config: SAMLConfiguration,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Configure SAML identity provider for a tenant."""
        try:
            config = await auth_provider.configure_saml(saml_config.tenant_id, saml_config)
            
            await auth_provider.log_audit_event(
                tenant_id=config.tenant_id,
                event_type=AuditEventType.CONFIGURATION_CHANGED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="configure_saml",
                result="success",
                details={"provider_name": config.name, "entity_id": config.entity_id}
            )
            
            return {"message": "SAML configuration created", "config_id": config.id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/auth/enterprise/saml/login", response_model=TokenResponse, tags=["Enterprise Authentication"])
    async def saml_login(
        saml_request: SAMLAuthRequest,
        request: Request,
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ) -> TokenResponse:
        """Authenticate user with SAML response."""
        try:
            user = await auth_provider.authenticate_saml(
                saml_request.saml_response,
                saml_request.relay_state
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SAML authentication failed"
                )

            # Generate access token
            access_token = auth_provider.jwt_handler.create_access_token(user)
            
            # Update last login
            await auth_provider.update_last_login(user.id)
            
            return TokenResponse(
                access_token=access_token,
                expires_in=auth_provider.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SAML authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SAML authentication failed"
            )

    # --- OAuth 2.0/OpenID Connect Endpoints ---
    @router.post("/auth/enterprise/oauth/configure", tags=["Enterprise Authentication"])
    async def configure_oauth(
        oauth_config: OAuthConfiguration,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Configure OAuth identity provider for a tenant."""
        try:
            config = await auth_provider.configure_oauth(oauth_config.tenant_id, oauth_config)
            
            await auth_provider.log_audit_event(
                tenant_id=config.tenant_id,
                event_type=AuditEventType.CONFIGURATION_CHANGED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="configure_oauth",
                result="success",
                details={"provider": config.provider.value, "name": config.name}
            )
            
            return {"message": "OAuth configuration created", "config_id": config.id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # --- Multi-Factor Authentication Endpoints ---
    @router.post("/auth/enterprise/mfa/setup", tags=["Enterprise Authentication"])
    async def setup_mfa(
        mfa_type: MFAType,
        request: Request,
        current_user: User = Depends(get_current_user),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider),
        phone_number: str = None,
        email: str = None
    ):
        """Setup multi-factor authentication."""
        try:
            mfa_config = await auth_provider.setup_mfa(
                current_user.id,
                mfa_type,
                phone_number=phone_number,
                email=email
            )
            
            response = {
                "mfa_id": mfa_config.id,
                "mfa_type": mfa_config.mfa_type,
                "setup_complete": True
            }
            
            if mfa_type == MFAType.TOTP:
                # Return QR code data for TOTP setup
                response["totp_secret"] = mfa_config.secret_key
                response["backup_codes"] = mfa_config.backup_codes
            
            return response
            
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # ===============================
    # COMPLIANCE MANAGEMENT ENDPOINTS
    # ===============================

    @router.post("/compliance/gdpr/requests", tags=["Compliance Management"])
    async def submit_gdpr_request(
        request_type: str,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        """Submit a GDPR data subject request."""
        if not gdpr_processor:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GDPR compliance module not available"
            )
        
        try:
            gdpr_request = await gdpr_processor.submit_data_subject_request(
                request_type, user_id, tenant_id, email
            )
            
            return {
                "request_id": gdpr_request.id,
                "request_type": gdpr_request.request_type,
                "status": gdpr_request.status,
                "verification_required": True,
                "message": f"GDPR {request_type} request submitted. Please check your email for verification."
            }
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"GDPR request submission failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit GDPR request"
            )

    @router.post("/compliance/soc2/controls/{control_id}/test", tags=["Compliance Management"])
    async def test_soc2_control(
        control_id: str,
        tester: str,
        test_description: str,
        test_results: Dict[str, Any],
        current_user: User = Depends(require_admin_role)
    ):
        """Perform and record a SOC 2 control test."""
        if not soc2_framework:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SOC 2 compliance module not available"
            )
        
        try:
            test_id = soc2_framework.perform_control_test(
                control_id, tester, test_description, test_results
            )
            
            return {
                "test_id": test_id,
                "control_id": control_id,
                "test_date": datetime.utcnow().isoformat(),
                "conclusion": test_results.get("conclusion", "inconclusive"),
                "message": "Control test recorded successfully"
            }
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"SOC 2 control test failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record control test"
            )

    @router.post("/compliance/hipaa/risk-assessment", tags=["Compliance Management"])
    async def conduct_hipaa_risk_assessment(
        assessment_scope: str,
        assessor: str,
        current_user: User = Depends(require_admin_role)
    ):
        """Conduct HIPAA risk assessment."""
        if not hipaa_framework:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="HIPAA compliance module not available"
            )
        
        try:
            assessment_id = hipaa_framework.conduct_risk_assessment(assessment_scope, assessor)
            
            return {
                "assessment_id": assessment_id,
                "assessment_date": datetime.utcnow().isoformat(),
                "scope": assessment_scope,
                "assessor": assessor,
                "message": "HIPAA risk assessment completed successfully"
            }
        except Exception as e:
            logger.error(f"HIPAA risk assessment failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to conduct HIPAA risk assessment"
            )

    @router.get("/compliance/dashboard/overview", tags=["Compliance Management"])
    async def get_compliance_overview(
        current_user: User = Depends(require_admin_role)
    ):
        """Get unified compliance dashboard overview."""
        try:
            # Basic framework status when modules are available
            frameworks_status = {}
            
            if gdpr_processor:
                frameworks_status["gdpr"] = {
                    "status": "operational",
                    "description": "GDPR data protection compliance active"
                }
            
            if soc2_framework:
                frameworks_status["soc2"] = {
                    "status": "operational", 
                    "description": "SOC 2 security controls active"
                }
            
            if hipaa_framework:
                frameworks_status["hipaa"] = {
                    "status": "operational",
                    "description": "HIPAA healthcare compliance active"
                }

            return {
                "dashboard_date": datetime.utcnow().isoformat(),
                "overall_compliance_status": "operational" if frameworks_status else "disabled",
                "frameworks": frameworks_status,
                "recent_activities": [
                    {
                        "framework": "Platform",
                        "activity": "Compliance modules initialized",
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "completed"
                    }
                ],
                "alerts": []
            }
        except Exception as e:
            logger.error(f"Compliance dashboard overview failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate compliance overview"
            )

    @router.get("/compliance/frameworks", tags=["Compliance Management"])
    async def list_compliance_frameworks():
        """List all supported compliance frameworks."""
        return {
            "frameworks": [
                {
                    "name": "GDPR",
                    "full_name": "General Data Protection Regulation",
                    "description": "EU data protection and privacy regulation",
                    "available": gdpr_processor is not None,
                    "features": [
                        "Data subject rights management",
                        "Consent management",
                        "Data breach notification",
                        "Privacy by design"
                    ]
                },
                {
                    "name": "SOC 2",
                    "full_name": "Service Organization Control 2",
                    "description": "Trust service criteria for service organizations",
                    "available": soc2_framework is not None,
                    "features": [
                        "Security controls",
                        "Availability monitoring",
                        "Processing integrity",
                        "Confidentiality protection",
                        "Privacy safeguards"
                    ]
                },
                {
                    "name": "HIPAA",
                    "full_name": "Health Insurance Portability and Accountability Act",
                    "description": "US healthcare data protection regulation",
                    "available": hipaa_framework is not None,
                    "features": [
                        "PHI protection",
                        "Risk assessments",
                        "Business associate agreements",
                        "Breach notification"
                    ]
                }
            ]
        }

    # ===============================
    # SYSTEM ADMINISTRATION ENDPOINTS
    # ===============================

    @router.get("/admin/vector/stats", tags=["System Administration"])
    async def vector_stats(
        vector_store: Annotated[VectorStore, Depends(get_vector_store)]
    ) -> dict:
        try:
            # Prefer stats() if available (FAISS)
            if hasattr(vector_store, "stats"):
                return await vector_store.stats()  # type: ignore[attr-defined]
            # Fallback: return vector count if available
            if hasattr(vector_store, "get_vector_store_size"):
                size = await vector_store.get_vector_store_size()  # type: ignore[attr-defined]
                return {"vectors": int(size)}
            return {"status": "unknown"}
        except Exception as e:
            admin_logger.error(f"vector_stats failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/admin/vector/rebuild", status_code=status.HTTP_202_ACCEPTED, tags=["System Administration"])
    async def vector_rebuild(
        vector_store: Annotated[VectorStore, Depends(get_vector_store)]
    ) -> dict:
        try:
            if hasattr(vector_store, "rebuild_index"):
                await vector_store.rebuild_index()  # type: ignore[attr-defined]
                return {"status": "ok", "message": "vector index rebuild started"}
            raise HTTPException(status_code=400, detail="Rebuild not supported")
        except HTTPException:
            raise
        except Exception as e:
            admin_logger.error(f"vector_rebuild failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/admin/integrity/check", tags=["System Administration"])
    async def integrity_check(
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    ) -> dict:
        try:
            # Count chunks in graph
            try:
                q = "MATCH (c:Chunk) RETURN count(c) AS n"
                rows = await graph_repo.execute_query(q)
                graph_chunks = 0
                if rows:
                    row = rows[0]
                    graph_chunks = int(row.get("n", 0) if isinstance(row, dict) else list(row.values())[0])
            except Exception:
                graph_chunks = 0
            # Count vectors in store
            vectors = 0
            if hasattr(vector_store, "stats"):
                stats = await vector_store.stats()  # type: ignore[attr-defined]
                vectors = int(stats.get("vectors", 0))
            elif hasattr(vector_store, "get_vector_store_size"):
                vectors = int(await vector_store.get_vector_store_size())  # type: ignore[attr-defined]
            ok = vectors >= 0 and graph_chunks >= 0
            warnings: list[str] = []
            if vectors < graph_chunks:
                warnings.append(
                    f"Vector count ({vectors}) is less than graph chunks ({graph_chunks}); some chunks may be missing embeddings."
                )
            return {"graph_chunks": graph_chunks, "vectors": vectors, "ok": ok, "warnings": warnings}
        except Exception as e:
            admin_logger.error(f"integrity_check failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/admin/health/detailed", response_model=SystemHealth, tags=["System Administration"])
    async def detailed_health_check(
        request: Request,
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        llm_service: Annotated[LLMService, Depends(get_llm)],
    ) -> SystemHealth:
        """Comprehensive health check with detailed component status."""
        health_checker = HealthChecker(timeout_seconds=10.0)

        # Get embedding service from vector store
        embedding_service = getattr(vector_store, 'embedding_service', None)

        # Define health checkers
        checkers = {
            "graph_repository": lambda: check_graph_repository(graph_repo),
            "vector_store": lambda: check_vector_store(vector_store),
            "llm_service": lambda: check_llm_service(llm_service),
        }

        if embedding_service:
            checkers["embedding_service"] = lambda: check_embedding_service(embedding_service)

        # Add system-level checks
        if hasattr(request.app.state, 'maintenance_scheduler'):
            async def check_maintenance_scheduler():
                scheduler = request.app.state.maintenance_scheduler
                if scheduler and hasattr(scheduler, 'is_running'):
                    return {
                        "status": "healthy" if scheduler.is_running() else "unhealthy",
                        "message": "Maintenance scheduler running" if scheduler.is_running() else "Maintenance scheduler stopped",
                        "details": {
                            "job_count": len(getattr(scheduler, 'jobs', [])),
                            "last_run": getattr(scheduler, 'last_run_time', None)
                        }
                    }
                else:
                    return {"status": "degraded", "message": "Maintenance scheduler not configured"}

            checkers["maintenance_scheduler"] = check_maintenance_scheduler

        return await health_checker.check_all(checkers)

    @router.get("/admin/performance/stats", tags=["System Administration"])
    async def performance_stats() -> dict:
        """Get performance statistics for monitored functions."""
        try:
            from graph_rag.api.performance import get_performance_stats
            return get_performance_stats()
        except ImportError:
            return {"status": "performance monitoring not available"}

    @router.get("/admin/cache/stats", tags=["System Administration"])
    async def cache_stats() -> dict:
        """Get cache statistics and hit rates."""
        try:
            from graph_rag.api.performance import get_cache_stats
            return get_cache_stats()
        except ImportError:
            return {"status": "cache monitoring not available"}

    @router.delete("/admin/cache/clear", tags=["System Administration"])
    async def clear_cache() -> dict:
        """Clear all cached data."""
        try:
            from graph_rag.api.performance import clear_cache
            clear_cache()
            return {"status": "ok", "message": "Cache cleared"}
        except ImportError:
            return {"status": "cache management not available", "message": "Cache clearing not supported"}

    @router.get("/admin/system/metrics", tags=["System Administration"])
    async def get_system_metrics_endpoint() -> dict:
        """Get comprehensive system metrics."""
        try:
            return get_system_metrics()
        except Exception as e:
            admin_logger.error(f"system metrics failed: {e}", exc_info=True)
            return {"error": str(e), "status": "metrics unavailable"}

    @router.get("/admin/platform/info", tags=["System Administration"])
    async def get_platform_info_endpoint() -> dict:
        """Get platform and environment information."""
        try:
            return get_platform_info()
        except Exception as e:
            admin_logger.error(f"platform info failed: {e}", exc_info=True)
            return {"error": str(e), "status": "platform info unavailable"}

    # ===============================
    # HEALTH AND STATUS ENDPOINTS
    # ===============================

    @router.get("/health/enterprise", tags=["Health Check"])
    async def enterprise_health_check(
        auth_provider: Optional[EnterpriseAuthProvider] = Depends(get_auth_provider)
    ):
        """Enterprise platform health check."""
        enterprise_features = {
            "authentication": True,
            "api_keys": True,
            "user_management": True
        }
        
        if hasattr(auth_provider, '_saml_configs'):
            enterprise_features.update({
                "saml_enabled": len(getattr(auth_provider, '_saml_configs', {})) > 0,
                "oauth_enabled": len(getattr(auth_provider, '_oauth_configs', {})) > 0,
                "ldap_enabled": len(getattr(auth_provider, '_ldap_configs', {})) > 0,
                "mfa_enabled": len(getattr(auth_provider, '_mfa_configs', {})) > 0,
                "audit_logging": len(getattr(auth_provider, '_audit_events', [])) > 0
            })

        return {
            "status": "healthy",
            "enterprise_features": enterprise_features,
            "compliance": {
                "gdpr_available": gdpr_processor is not None,
                "soc2_available": soc2_framework is not None,
                "hipaa_available": hipaa_framework is not None
            },
            "tenant_count": len(getattr(auth_provider, '_tenants', {})) if hasattr(auth_provider, '_tenants') else 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    @router.get("/health", tags=["Health Check"])
    async def platform_health():
        """Basic platform health check."""
        return {
            "status": "healthy",
            "service": "Enterprise Platform",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }

    return router


# Factory function for use in main.py
def create_enterprise_platform_router_factory() -> APIRouter:
    """Create and configure the Enterprise Platform consolidated router"""
    return create_enterprise_platform_router()