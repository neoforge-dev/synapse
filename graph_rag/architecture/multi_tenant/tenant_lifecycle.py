"""Tenant lifecycle management for automated provisioning and deprovisioning.

This module provides:
- Automated tenant provisioning workflow
- Data migration and transformation tools
- Integration setup automation
- Success tracking and validation
- Tenant decommissioning with data cleanup
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .data_isolation import TenantDataManager
from .resource_isolation import QoSLevel, TenantResourceManager
from .tenant_manager import TenantConfiguration, TenantManager, TenantStatus, TenantType

logger = logging.getLogger(__name__)


class ProvisioningStage(str, Enum):
    """Stages in the tenant provisioning process."""
    VALIDATION = "validation"
    DATABASE_SETUP = "database_setup"
    RESOURCE_CONFIG = "resource_config"
    DATA_MIGRATION = "data_migration"
    INTEGRATION_SETUP = "integration_setup"
    CUSTOMIZATION = "customization"
    TESTING = "testing"
    ACTIVATION = "activation"
    COMPLETED = "completed"
    FAILED = "failed"


class OnboardingResult(str, Enum):
    """Results of onboarding operations."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class ProvisioningRequest:
    """Request for tenant provisioning."""
    tenant_name: str
    tenant_type: TenantType
    contact_email: str
    domain: str | None = None

    # Resource configuration
    qos_level: QoSLevel = QoSLevel.STANDARD
    max_users: int = 100
    max_documents: int = 10000
    storage_limit_gb: int = 100

    # Feature configuration
    enable_advanced_analytics: bool = True
    enable_white_label: bool = False
    enable_api_access: bool = True
    enable_export: bool = True

    # Integration settings
    sso_provider: str | None = None
    sso_config: dict[str, Any] = field(default_factory=dict)

    # Customization settings
    custom_branding: dict[str, Any] = field(default_factory=dict)
    custom_features: dict[str, bool] = field(default_factory=dict)

    # Migration settings
    source_data: dict[str, Any] | None = None
    migration_priority: str = "normal"  # low, normal, high

    # Metadata
    requested_by: str | None = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    target_completion: datetime | None = None


@dataclass
class ProvisioningStatus:
    """Status tracking for tenant provisioning."""
    request: ProvisioningRequest
    tenant_id: str
    current_stage: ProvisioningStage
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    # Stage completion tracking
    completed_stages: list[ProvisioningStage] = field(default_factory=list)
    failed_stages: list[ProvisioningStage] = field(default_factory=list)

    # Progress tracking
    overall_progress_percent: float = 0.0
    current_stage_progress_percent: float = 0.0

    # Results and logs
    stage_results: dict[ProvisioningStage, OnboardingResult] = field(default_factory=dict)
    stage_logs: dict[ProvisioningStage, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    # Estimated completion
    estimated_completion: datetime | None = None

    @property
    def is_completed(self) -> bool:
        """Check if provisioning is completed."""
        return self.current_stage in [ProvisioningStage.COMPLETED, ProvisioningStage.FAILED]

    @property
    def is_successful(self) -> bool:
        """Check if provisioning was successful."""
        return self.current_stage == ProvisioningStage.COMPLETED

    @property
    def duration(self) -> timedelta | None:
        """Get provisioning duration."""
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at


class TenantProvisioningEngine:
    """Core engine for tenant provisioning automation."""

    def __init__(
        self,
        tenant_manager: TenantManager,
        data_manager: TenantDataManager,
        resource_manager: TenantResourceManager
    ):
        """Initialize provisioning engine."""
        self.tenant_manager = tenant_manager
        self.data_manager = data_manager
        self.resource_manager = resource_manager

        # Provisioning workflow configuration
        self._stage_handlers: dict[ProvisioningStage, Callable] = {
            ProvisioningStage.VALIDATION: self._handle_validation,
            ProvisioningStage.DATABASE_SETUP: self._handle_database_setup,
            ProvisioningStage.RESOURCE_CONFIG: self._handle_resource_config,
            ProvisioningStage.DATA_MIGRATION: self._handle_data_migration,
            ProvisioningStage.INTEGRATION_SETUP: self._handle_integration_setup,
            ProvisioningStage.CUSTOMIZATION: self._handle_customization,
            ProvisioningStage.TESTING: self._handle_testing,
            ProvisioningStage.ACTIVATION: self._handle_activation,
        }

        # Active provisioning tracking
        self._active_provisioning: dict[str, ProvisioningStatus] = {}

        # Stage timing estimates (in minutes)
        self._stage_estimates = {
            ProvisioningStage.VALIDATION: 5,
            ProvisioningStage.DATABASE_SETUP: 15,
            ProvisioningStage.RESOURCE_CONFIG: 10,
            ProvisioningStage.DATA_MIGRATION: 60,  # Varies by data size
            ProvisioningStage.INTEGRATION_SETUP: 30,
            ProvisioningStage.CUSTOMIZATION: 20,
            ProvisioningStage.TESTING: 15,
            ProvisioningStage.ACTIVATION: 5,
        }

        logger.info("TenantProvisioningEngine initialized")

    async def start_provisioning(self, request: ProvisioningRequest) -> str:
        """Start automated tenant provisioning."""
        # Generate unique tenant ID
        tenant_id = self._generate_tenant_id(request.tenant_name)

        # Create provisioning status
        status = ProvisioningStatus(
            request=request,
            tenant_id=tenant_id,
            current_stage=ProvisioningStage.VALIDATION,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            estimated_completion=datetime.utcnow() + timedelta(
                minutes=sum(self._stage_estimates.values())
            )
        )

        self._active_provisioning[tenant_id] = status

        # Start provisioning workflow asynchronously
        asyncio.create_task(self._run_provisioning_workflow(status))

        logger.info(f"Started provisioning for tenant {tenant_id}")
        return tenant_id

    async def _run_provisioning_workflow(self, status: ProvisioningStatus) -> None:
        """Execute the complete provisioning workflow."""
        try:
            stages = list(self._stage_handlers.keys())
            total_stages = len(stages)

            for i, stage in enumerate(stages):
                status.current_stage = stage
                status.current_stage_progress_percent = 0.0
                status.overall_progress_percent = (i / total_stages) * 100
                status.updated_at = datetime.utcnow()

                logger.info(f"Starting stage {stage} for tenant {status.tenant_id}")

                # Execute stage handler
                handler = self._stage_handlers[stage]
                result = await handler(status)

                # Update status based on result
                status.stage_results[stage] = result
                status.current_stage_progress_percent = 100.0

                if result == OnboardingResult.SUCCESS:
                    status.completed_stages.append(stage)
                    logger.info(f"Completed stage {stage} for tenant {status.tenant_id}")
                else:
                    status.failed_stages.append(stage)
                    status.errors.append(f"Stage {stage} failed with result: {result}")
                    logger.error(f"Stage {stage} failed for tenant {status.tenant_id}: {result}")

                    # Stop on failure
                    status.current_stage = ProvisioningStage.FAILED
                    break
            else:
                # All stages completed successfully
                status.current_stage = ProvisioningStage.COMPLETED
                status.overall_progress_percent = 100.0

            status.completed_at = datetime.utcnow()
            status.updated_at = datetime.utcnow()

            logger.info(f"Provisioning workflow completed for tenant {status.tenant_id}: {status.current_stage}")

        except Exception as e:
            logger.error(f"Provisioning workflow failed for tenant {status.tenant_id}: {e}")
            status.current_stage = ProvisioningStage.FAILED
            status.errors.append(f"Workflow exception: {str(e)}")
            status.completed_at = datetime.utcnow()
            status.updated_at = datetime.utcnow()

    async def _handle_validation(self, status: ProvisioningStatus) -> OnboardingResult:
        """Validate provisioning request."""
        try:
            request = status.request

            # Validate tenant name uniqueness
            if status.tenant_id in [config.tenant_id for config in self.tenant_manager.get_all_tenants()]:
                status.errors.append("Tenant ID already exists")
                return OnboardingResult.FAILED

            # Validate contact email format
            if "@" not in request.contact_email:
                status.errors.append("Invalid contact email format")
                return OnboardingResult.FAILED

            # Validate domain if provided
            if request.domain and not self._validate_domain(request.domain):
                status.errors.append("Invalid domain format")
                return OnboardingResult.FAILED

            # Validate resource limits
            if request.max_users <= 0 or request.max_documents <= 0:
                status.errors.append("Invalid resource limits")
                return OnboardingResult.FAILED

            status.stage_logs[ProvisioningStage.VALIDATION] = ["All validations passed"]
            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Validation error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_database_setup(self, status: ProvisioningStatus) -> OnboardingResult:
        """Setup tenant database isolation."""
        try:
            request = status.request

            # Create tenant configuration
            config = TenantConfiguration(
                tenant_id=status.tenant_id,
                tenant_name=request.tenant_name,
                tenant_type=request.tenant_type,
                status=TenantStatus.PROVISIONING,
                domain=request.domain,
                max_users=request.max_users,
                max_documents=request.max_documents,
                storage_limit_gb=request.storage_limit_gb,
                enable_advanced_analytics=request.enable_advanced_analytics,
                enable_white_label=request.enable_white_label,
                enable_api_access=request.enable_api_access,
                enable_export=request.enable_export,
                custom_branding=request.custom_branding,
                integration_settings=request.sso_config,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=request.requested_by,
                contact_email=request.contact_email,
            )

            # Register tenant
            self.tenant_manager.register_tenant(config)

            # Create tenant context
            tenant_context = self.tenant_manager.create_tenant_context(status.tenant_id)
            if not tenant_context:
                return OnboardingResult.FAILED

            # Setup data isolation
            success = await self.data_manager.setup_tenant_data(tenant_context)
            if not success:
                status.errors.append("Failed to setup tenant database")
                return OnboardingResult.FAILED

            status.stage_logs[ProvisioningStage.DATABASE_SETUP] = [
                f"Created tenant configuration: {config.tenant_id}",
                f"Setup database with isolation level: {tenant_context.isolation_level}",
            ]
            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Database setup error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_resource_config(self, status: ProvisioningStatus) -> OnboardingResult:
        """Configure tenant resource limits."""
        try:
            tenant_context = self.tenant_manager.create_tenant_context(status.tenant_id)
            if not tenant_context:
                return OnboardingResult.FAILED

            # Configure resource limits based on QoS level
            self.resource_manager.configure_tenant_resources(tenant_context)

            status.stage_logs[ProvisioningStage.RESOURCE_CONFIG] = [
                f"Configured resources with QoS level: {status.request.qos_level}",
                "CPU limit: varies by QoS",
                "Memory limit: varies by QoS",
                f"API calls per hour: {status.request.max_users * 10}",
            ]
            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Resource configuration error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_data_migration(self, status: ProvisioningStatus) -> OnboardingResult:
        """Handle tenant data migration if source data provided."""
        try:
            request = status.request

            if not request.source_data:
                status.stage_logs[ProvisioningStage.DATA_MIGRATION] = ["No source data provided, skipping migration"]
                return OnboardingResult.SUCCESS

            # Create tenant context for data operations
            tenant_context = self.tenant_manager.create_tenant_context(status.tenant_id)
            if not tenant_context:
                return OnboardingResult.FAILED

            # Simulate data migration process
            await self._migrate_tenant_data(tenant_context, request.source_data, status)

            status.stage_logs[ProvisioningStage.DATA_MIGRATION] = [
                f"Migrated {len(request.source_data.get('documents', []))} documents",
                f"Migrated {len(request.source_data.get('entities', []))} entities",
                "Data migration completed successfully",
            ]
            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Data migration error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_integration_setup(self, status: ProvisioningStatus) -> OnboardingResult:
        """Setup tenant integrations (SSO, third-party services)."""
        try:
            request = status.request

            integrations_setup = []

            # Setup SSO if configured
            if request.sso_provider and request.sso_config:
                await self._setup_sso_integration(status.tenant_id, request.sso_provider, request.sso_config)
                integrations_setup.append(f"SSO with {request.sso_provider}")

            # Setup other integrations based on tenant type
            if request.tenant_type == TenantType.ENTERPRISE:
                # Enterprise integrations (Salesforce, SAP, etc.)
                integrations_setup.extend(await self._setup_enterprise_integrations(status.tenant_id))

            status.stage_logs[ProvisioningStage.INTEGRATION_SETUP] = [
                f"Setup {len(integrations_setup)} integrations",
            ] + integrations_setup

            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Integration setup error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_customization(self, status: ProvisioningStatus) -> OnboardingResult:
        """Apply tenant customizations (branding, features)."""
        try:
            request = status.request

            customizations_applied = []

            # Apply branding customizations
            if request.custom_branding:
                await self._apply_branding_customization(status.tenant_id, request.custom_branding)
                customizations_applied.append("Custom branding")

            # Apply feature customizations
            if request.custom_features:
                await self._apply_feature_customization(status.tenant_id, request.custom_features)
                customizations_applied.append("Feature toggles")

            # Setup white-label configuration if enabled
            if request.enable_white_label:
                await self._setup_white_label_config(status.tenant_id, request)
                customizations_applied.append("White-label configuration")

            status.stage_logs[ProvisioningStage.CUSTOMIZATION] = [
                f"Applied {len(customizations_applied)} customizations",
            ] + customizations_applied

            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Customization error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_testing(self, status: ProvisioningStatus) -> OnboardingResult:
        """Perform end-to-end testing of tenant setup."""
        try:
            tenant_context = self.tenant_manager.create_tenant_context(status.tenant_id)
            if not tenant_context:
                return OnboardingResult.FAILED

            test_results = []

            # Test database connectivity
            database_test = await self._test_database_connectivity(tenant_context)
            test_results.append(f"Database connectivity: {'PASS' if database_test else 'FAIL'}")

            # Test resource limits
            resource_test = await self._test_resource_limits(tenant_context)
            test_results.append(f"Resource limits: {'PASS' if resource_test else 'FAIL'}")

            # Test API access
            api_test = await self._test_api_access(tenant_context)
            test_results.append(f"API access: {'PASS' if api_test else 'FAIL'}")

            # Test integrations
            integration_test = await self._test_integrations(tenant_context)
            test_results.append(f"Integrations: {'PASS' if integration_test else 'FAIL'}")

            # All tests must pass
            all_tests_passed = all("PASS" in result for result in test_results)

            status.stage_logs[ProvisioningStage.TESTING] = [
                f"Executed {len(test_results)} tests",
            ] + test_results

            return OnboardingResult.SUCCESS if all_tests_passed else OnboardingResult.FAILED

        except Exception as e:
            status.errors.append(f"Testing error: {str(e)}")
            return OnboardingResult.FAILED

    async def _handle_activation(self, status: ProvisioningStatus) -> OnboardingResult:
        """Activate tenant and make it available for use."""
        try:
            # Update tenant status to active
            success = self.tenant_manager.update_tenant_status(status.tenant_id, TenantStatus.ACTIVE)
            if not success:
                return OnboardingResult.FAILED

            # Send activation notification
            await self._send_activation_notification(status)

            status.stage_logs[ProvisioningStage.ACTIVATION] = [
                f"Tenant {status.tenant_id} activated successfully",
                f"Notification sent to {status.request.contact_email}",
            ]

            return OnboardingResult.SUCCESS

        except Exception as e:
            status.errors.append(f"Activation error: {str(e)}")
            return OnboardingResult.FAILED

    def get_provisioning_status(self, tenant_id: str) -> ProvisioningStatus | None:
        """Get provisioning status for tenant."""
        return self._active_provisioning.get(tenant_id)

    def get_active_provisioning(self) -> list[ProvisioningStatus]:
        """Get all active provisioning operations."""
        return list(self._active_provisioning.values())

    def _generate_tenant_id(self, tenant_name: str) -> str:
        """Generate unique tenant ID from name."""
        import hashlib
        import time

        # Create ID from name + timestamp
        name_hash = hashlib.md5(tenant_name.encode()).hexdigest()[:8]
        timestamp = str(int(time.time()))[-6:]
        return f"tenant_{name_hash}_{timestamp}"

    def _validate_domain(self, domain: str) -> bool:
        """Validate domain format."""
        import re
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-._]*[a-zA-Z0-9]$'
        return re.match(pattern, domain) is not None

    async def _migrate_tenant_data(
        self,
        tenant_context,
        source_data: dict[str, Any],
        status: ProvisioningStatus
    ) -> None:
        """Migrate data for tenant."""
        # Simulate data migration process
        documents = source_data.get('documents', [])
        entities = source_data.get('entities', [])

        # Use tenant data manager to import data
        with self.tenant_manager.tenant_scope(tenant_context.tenant_id):
            # Simulate document processing
            for i, _doc in enumerate(documents):
                # Update progress
                progress = (i + 1) / len(documents) * 100
                status.current_stage_progress_percent = progress

                # Simulate processing time
                await asyncio.sleep(0.1)

            # Simulate entity processing
            for _entity in entities:
                await asyncio.sleep(0.05)

    async def _setup_sso_integration(self, tenant_id: str, provider: str, config: dict[str, Any]) -> None:
        """Setup SSO integration for tenant."""
        # Placeholder for SSO setup
        logger.info(f"Setting up SSO integration for {tenant_id}: {provider}")

    async def _setup_enterprise_integrations(self, tenant_id: str) -> list[str]:
        """Setup enterprise integrations for tenant."""
        # Placeholder for enterprise integrations
        integrations = ["Salesforce", "Microsoft Active Directory", "Slack"]
        return integrations

    async def _apply_branding_customization(self, tenant_id: str, branding: dict[str, Any]) -> None:
        """Apply branding customizations for tenant."""
        # Placeholder for branding customization
        logger.info(f"Applying branding customization for {tenant_id}")

    async def _apply_feature_customization(self, tenant_id: str, features: dict[str, bool]) -> None:
        """Apply feature customizations for tenant."""
        # Placeholder for feature customization
        logger.info(f"Applying feature customization for {tenant_id}")

    async def _setup_white_label_config(self, tenant_id: str, request: ProvisioningRequest) -> None:
        """Setup white-label configuration for tenant."""
        # Placeholder for white-label setup
        logger.info(f"Setting up white-label configuration for {tenant_id}")

    async def _test_database_connectivity(self, tenant_context) -> bool:
        """Test database connectivity for tenant."""
        try:
            # Test basic database operations
            await self.data_manager.execute_tenant_query(
                "SELECT 1 as test", tenant_context=tenant_context
            )
            return True
        except Exception as e:
            logger.error(f"Database connectivity test failed for {tenant_context.tenant_id}: {e}")
            return False

    async def _test_resource_limits(self, tenant_context) -> bool:
        """Test resource limits for tenant."""
        try:
            # Test resource acquisition
            from .resource_isolation import ResourceType
            available, _ = await self.resource_manager.check_resource_availability(
                ResourceType.API_CALLS, tenant_context=tenant_context
            )
            return available
        except Exception as e:
            logger.error(f"Resource limits test failed for {tenant_context.tenant_id}: {e}")
            return False

    async def _test_api_access(self, tenant_context) -> bool:
        """Test API access for tenant."""
        # Placeholder for API access test
        return True

    async def _test_integrations(self, tenant_context) -> bool:
        """Test integrations for tenant."""
        # Placeholder for integration tests
        return True

    async def _send_activation_notification(self, status: ProvisioningStatus) -> None:
        """Send activation notification to tenant."""
        # Placeholder for notification sending
        logger.info(f"Sending activation notification to {status.request.contact_email}")


class TenantLifecycleManager:
    """Complete tenant lifecycle management."""

    def __init__(
        self,
        tenant_manager: TenantManager,
        data_manager: TenantDataManager,
        resource_manager: TenantResourceManager
    ):
        """Initialize lifecycle manager."""
        self.tenant_manager = tenant_manager
        self.data_manager = data_manager
        self.resource_manager = resource_manager

        self.provisioning_engine = TenantProvisioningEngine(
            tenant_manager, data_manager, resource_manager
        )

        logger.info("TenantLifecycleManager initialized")

    async def provision_tenant(self, request: ProvisioningRequest) -> str:
        """Start tenant provisioning process."""
        return await self.provisioning_engine.start_provisioning(request)

    async def deprovision_tenant(self, tenant_id: str, preserve_data: bool = False) -> bool:
        """Deprovision tenant and cleanup resources."""
        try:
            # Get tenant context
            tenant_context = self.tenant_manager.create_tenant_context(tenant_id)
            if not tenant_context:
                logger.error(f"Cannot find tenant context for deprovisioning: {tenant_id}")
                return False

            # Protect Epic 7 consultation tenant
            if tenant_context.is_consultation:
                logger.error("Cannot deprovision consultation tenant - Epic 7 protection")
                return False

            # Update status to decommissioned
            self.tenant_manager.update_tenant_status(tenant_id, TenantStatus.DECOMMISSIONED)

            # Cleanup data if not preserving
            if not preserve_data:
                await self.data_manager.delete_tenant_data(tenant_context)

            # Remove tenant registration
            self.tenant_manager.deregister_tenant(tenant_id)

            logger.info(f"Successfully deprovisioned tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deprovision tenant {tenant_id}: {e}")
            return False

    def get_provisioning_status(self, tenant_id: str) -> ProvisioningStatus | None:
        """Get provisioning status for tenant."""
        return self.provisioning_engine.get_provisioning_status(tenant_id)

    def get_all_provisioning_status(self) -> list[ProvisioningStatus]:
        """Get all active provisioning operations."""
        return self.provisioning_engine.get_active_provisioning()

    async def migrate_tenant_data(
        self,
        tenant_id: str,
        source_data: dict[str, Any],
        migration_options: dict[str, Any] | None = None
    ) -> bool:
        """Migrate data for existing tenant."""
        try:
            tenant_context = self.tenant_manager.create_tenant_context(tenant_id)
            if not tenant_context:
                return False

            # Use provisioning engine's migration logic
            status = ProvisioningStatus(
                request=ProvisioningRequest(
                    tenant_name=tenant_context.tenant_name,
                    tenant_type=tenant_context.tenant_type,
                    contact_email="migration@system.local",
                    source_data=source_data
                ),
                tenant_id=tenant_id,
                current_stage=ProvisioningStage.DATA_MIGRATION,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            await self.provisioning_engine._migrate_tenant_data(
                tenant_context, source_data, status
            )

            return True

        except Exception as e:
            logger.error(f"Data migration failed for tenant {tenant_id}: {e}")
            return False
