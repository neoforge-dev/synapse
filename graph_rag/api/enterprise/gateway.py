"""Enterprise API Gateway with comprehensive monitoring, rate limiting, and SLA management."""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...compliance.audit_logging import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    ComplianceAuditLogger,
)
from ...config.enterprise_config import EnterpriseConfigManager
from ..auth.enterprise_rbac import EnterpriseRBACManager
from .monitoring import EnterpriseMonitor, HealthStatus
from .rate_limiting import RateLimiter, RateLimitExceeded, RateLimitTier
from .sla_manager import SLAManager

logger = logging.getLogger(__name__)


class APIMetrics(BaseModel):
    """API metrics for monitoring and reporting."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0

    # Response time metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Error metrics
    error_rate_percentage: float = 0.0
    timeout_count: int = 0
    server_error_count: int = 0

    # Resource utilization
    active_connections: int = 0
    peak_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percentage: float = 0.0

    # SLA metrics
    sla_compliance_percentage: float = 100.0
    sla_violations: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RequestMetadata(BaseModel):
    """Request metadata for tracking and monitoring."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str | None = None
    client_id: str | None = None
    user_id: UUID | None = None

    # Request details
    method: str
    path: str
    user_agent: str | None = None
    source_ip: str

    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    response_time_ms: float | None = None

    # Response details
    status_code: int | None = None
    response_size_bytes: int = 0
    error_message: str | None = None

    # Security context
    authenticated: bool = False
    rate_limit_tier: RateLimitTier | None = None
    permission_checks: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class EnterpriseGatewayMiddleware(BaseHTTPMiddleware):
    """Comprehensive enterprise middleware for API gateway functionality."""

    def __init__(self, app: FastAPI, gateway: "EnterpriseAPIGateway"):
        super().__init__(app)
        self.gateway = gateway

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through enterprise gateway controls."""

        # Create request metadata
        metadata = RequestMetadata(
            method=request.method,
            path=str(request.url.path),
            user_agent=request.headers.get("user-agent"),
            source_ip=request.client.host if request.client else "unknown"
        )

        try:
            # Pre-request processing
            await self.gateway._process_incoming_request(request, metadata)

            # Execute request
            response = await call_next(request)

            # Post-request processing
            await self.gateway._process_outgoing_response(request, response, metadata)

            return response

        except RateLimitExceeded as e:
            # Handle rate limiting
            return await self.gateway._handle_rate_limit_exceeded(e, metadata)

        except HTTPException as e:
            # Handle HTTP exceptions
            return await self.gateway._handle_http_exception(e, metadata)

        except Exception as e:
            # Handle unexpected errors
            return await self.gateway._handle_unexpected_error(e, metadata)


class EnterpriseAPIGateway:
    """Comprehensive enterprise API gateway with monitoring, rate limiting, and compliance."""

    def __init__(self, config_manager: EnterpriseConfigManager,
                 audit_logger: ComplianceAuditLogger,
                 rbac_manager: EnterpriseRBACManager):

        self.config_manager = config_manager
        self.audit_logger = audit_logger
        self.rbac_manager = rbac_manager

        # Core components
        self.rate_limiter = RateLimiter(audit_logger)
        self.monitor = EnterpriseMonitor()
        self.sla_manager = SLAManager(audit_logger)

        # Request tracking
        self.active_requests: dict[str, RequestMetadata] = {}
        self.metrics_history: list[APIMetrics] = []

        # Global counters
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0

        # Response time tracking
        self.response_times: list[float] = []
        self.max_response_times = 10000  # Keep last 10k response times

        # Background tasks
        self._metrics_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None

        logger.info("Enterprise API Gateway initialized")

    async def _process_incoming_request(self, request: Request, metadata: RequestMetadata) -> None:
        """Process incoming request with enterprise controls."""

        # Extract authentication context
        auth_header = request.headers.get("authorization")
        api_key = request.headers.get("x-api-key")

        tenant_id = None
        client_id = None
        user_id = None
        rate_limit_tier = RateLimitTier.BASIC

        # TODO: Integrate with actual authentication system
        # For now, use placeholder logic
        if auth_header or api_key:
            metadata.authenticated = True
            # Extract from JWT or API key lookup
            tenant_id = request.headers.get("x-tenant-id", "default")
            client_id = request.headers.get("x-client-id", "default")

            # Get tenant configuration to determine rate limit tier
            tenant_config = await self.config_manager.get_tenant_configuration(tenant_id)
            if tenant_config:
                # Determine tier based on tenant configuration
                enterprise_client = self.config_manager.get_enterprise_client(tenant_config.client_id)
                if enterprise_client:
                    if enterprise_client.contract_value >= 500000:
                        rate_limit_tier = RateLimitTier.PREMIUM
                    elif enterprise_client.contract_value >= 150000:
                        rate_limit_tier = RateLimitTier.ENTERPRISE
                    elif enterprise_client.contract_value >= 50000:
                        rate_limit_tier = RateLimitTier.PROFESSIONAL

        # Update metadata
        metadata.tenant_id = tenant_id
        metadata.client_id = client_id
        metadata.user_id = user_id
        metadata.rate_limit_tier = rate_limit_tier

        # Apply rate limiting
        if client_id and tenant_id:
            # Calculate request size
            content_length = request.headers.get("content-length", "0")
            request_size_mb = int(content_length) / (1024 * 1024) if content_length.isdigit() else 0.0

            # Check rate limits
            await self.rate_limiter.check_rate_limits(client_id, tenant_id, rate_limit_tier, request_size_mb)
            await self.rate_limiter.start_request(client_id)

        # Health check
        health_status = await self.monitor.get_health_status()
        if health_status.status == HealthStatus.CRITICAL:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        # Store request metadata
        self.active_requests[metadata.request_id] = metadata

        # Update counters
        self.total_requests += 1

        # Audit logging
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.API_CALL,
            tenant_id=tenant_id,
            user_id=user_id,
            source_ip=metadata.source_ip,
            user_agent=metadata.user_agent,
            api_endpoint=metadata.path,
            http_method=metadata.method,
            action=f"API request: {metadata.method} {metadata.path}",
            details={
                "request_id": metadata.request_id,
                "authenticated": metadata.authenticated,
                "rate_limit_tier": rate_limit_tier.value if rate_limit_tier else None
            }
        ))

    async def _process_outgoing_response(self, request: Request, response: Response,
                                       metadata: RequestMetadata) -> None:
        """Process outgoing response and collect metrics."""

        # Update metadata
        metadata.end_time = datetime.utcnow()
        metadata.response_time_ms = (metadata.end_time - metadata.start_time).total_seconds() * 1000
        metadata.status_code = response.status_code

        # Get response size if available
        if hasattr(response, 'body') and response.body:
            metadata.response_size_bytes = len(response.body)

        # Update counters
        if response.status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Track response time
        self.response_times.append(metadata.response_time_ms)
        if len(self.response_times) > self.max_response_times:
            self.response_times.pop(0)

        # Check SLA compliance
        if metadata.tenant_id:
            sla = await self.sla_manager.get_sla(metadata.tenant_id)
            if sla:
                await self.sla_manager.record_request(
                    metadata.tenant_id,
                    metadata.response_time_ms,
                    response.status_code < 400
                )

        # End concurrent request tracking
        if metadata.client_id:
            await self.rate_limiter.end_request(metadata.client_id)

        # Remove from active requests
        if metadata.request_id in self.active_requests:
            del self.active_requests[metadata.request_id]

        # Monitor health metrics
        await self.monitor.record_request(
            response_time_ms=metadata.response_time_ms,
            success=response.status_code < 400,
            endpoint=metadata.path
        )

        # Detailed audit log for completed request
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.API_CALL,
            tenant_id=metadata.tenant_id,
            user_id=metadata.user_id,
            source_ip=metadata.source_ip,
            user_agent=metadata.user_agent,
            api_endpoint=metadata.path,
            http_method=metadata.method,
            action=f"API response: {metadata.method} {metadata.path}",
            outcome="success" if response.status_code < 400 else "failure",
            details={
                "request_id": metadata.request_id,
                "status_code": response.status_code,
                "response_time_ms": metadata.response_time_ms,
                "response_size_bytes": metadata.response_size_bytes
            }
        ))

    async def _handle_rate_limit_exceeded(self, error: RateLimitExceeded,
                                        metadata: RequestMetadata) -> JSONResponse:
        """Handle rate limit exceeded error."""

        self.rate_limited_requests += 1
        metadata.end_time = datetime.utcnow()
        metadata.response_time_ms = (metadata.end_time - metadata.start_time).total_seconds() * 1000
        metadata.status_code = 429
        metadata.error_message = str(error)

        # Remove from active requests
        if metadata.request_id in self.active_requests:
            del self.active_requests[metadata.request_id]

        headers = {"X-RateLimit-Limit": str(error.limit)}
        if error.retry_after:
            headers["Retry-After"] = str(error.retry_after)

        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": str(error),
                "request_id": metadata.request_id,
                "limit_type": error.limit_type.value,
                "limit": error.limit,
                "current": error.current
            },
            headers=headers
        )

    async def _handle_http_exception(self, error: HTTPException,
                                   metadata: RequestMetadata) -> JSONResponse:
        """Handle HTTP exception."""

        self.failed_requests += 1
        metadata.end_time = datetime.utcnow()
        metadata.response_time_ms = (metadata.end_time - metadata.start_time).total_seconds() * 1000
        metadata.status_code = error.status_code
        metadata.error_message = error.detail

        # Remove from active requests
        if metadata.request_id in self.active_requests:
            del self.active_requests[metadata.request_id]

        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": "http_exception",
                "message": error.detail,
                "request_id": metadata.request_id
            },
            headers=getattr(error, 'headers', {})
        )

    async def _handle_unexpected_error(self, error: Exception,
                                     metadata: RequestMetadata) -> JSONResponse:
        """Handle unexpected error."""

        self.failed_requests += 1
        metadata.end_time = datetime.utcnow()
        metadata.response_time_ms = (metadata.end_time - metadata.start_time).total_seconds() * 1000
        metadata.status_code = 500
        metadata.error_message = str(error)

        # Remove from active requests
        if metadata.request_id in self.active_requests:
            del self.active_requests[metadata.request_id]

        # Log unexpected error
        logger.error(f"Unexpected error in API gateway: {error}", exc_info=True)

        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SECURITY_INCIDENT,
            tenant_id=metadata.tenant_id,
            user_id=metadata.user_id,
            source_ip=metadata.source_ip,
            action="Unexpected error in API gateway",
            outcome="failure",
            severity=AuditSeverity.HIGH,
            details={
                "request_id": metadata.request_id,
                "error": str(error),
                "path": metadata.path,
                "method": metadata.method
            }
        ))

        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "request_id": metadata.request_id
            }
        )

    async def get_current_metrics(self) -> APIMetrics:
        """Get current API metrics."""

        now = datetime.utcnow()

        # Calculate response time percentiles
        if self.response_times:
            sorted_times = sorted(self.response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)

            avg_response_time = sum(sorted_times) / len(sorted_times)
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else 0
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else 0
        else:
            avg_response_time = 0
            p95_response_time = 0
            p99_response_time = 0

        # Calculate error rate
        error_rate = (self.failed_requests / max(1, self.total_requests)) * 100

        # Get SLA compliance
        sla_compliance = 100.0  # Default
        sla_violations = 0

        # Get health status
        health_status = await self.monitor.get_health_status()

        return APIMetrics(
            timestamp=now,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            rate_limited_requests=self.rate_limited_requests,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            error_rate_percentage=error_rate,
            timeout_count=0,  # TODO: Implement timeout tracking
            server_error_count=self.failed_requests,
            active_connections=len(self.active_requests),
            peak_connections=0,  # TODO: Track peak connections
            memory_usage_mb=health_status.memory_usage_mb,
            cpu_usage_percentage=health_status.cpu_usage_percentage,
            sla_compliance_percentage=sla_compliance,
            sla_violations=sla_violations
        )

    async def get_tenant_metrics(self, tenant_id: str, hours: int = 24) -> dict[str, Any]:
        """Get metrics for a specific tenant."""

        # Get rate limiter usage
        client_usage = {}
        for client_id, state in self.rate_limiter.client_states.items():
            if state.tenant_id == tenant_id:
                usage = await self.rate_limiter.get_client_usage(client_id)
                if usage:
                    client_usage[client_id] = usage

        # Get SLA status
        sla = await self.sla_manager.get_sla(tenant_id)
        sla_status = None
        if sla:
            sla_status = await self.sla_manager.get_sla_status(tenant_id)

        # Get compliance audit statistics
        compliance_stats = await self.audit_logger.get_compliance_statistics(tenant_id, hours * 24)

        return {
            "tenant_id": tenant_id,
            "time_period_hours": hours,
            "client_usage": client_usage,
            "sla_status": sla_status,
            "compliance_statistics": compliance_stats,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def get_enterprise_dashboard(self) -> dict[str, Any]:
        """Get comprehensive enterprise dashboard data."""

        current_metrics = await self.get_current_metrics()
        health_status = await self.monitor.get_health_status()
        rate_limiter_stats = await self.rate_limiter.get_global_statistics()

        # Get high-value clients
        high_value_clients = self.config_manager.get_high_value_clients()

        return {
            "api_metrics": current_metrics.dict(),
            "health_status": health_status.dict(),
            "rate_limiting": rate_limiter_stats,
            "high_value_clients": len(high_value_clients),
            "total_enterprise_contracts": sum(c.contract_value for c in high_value_clients),
            "active_requests": len(self.active_requests),
            "generated_at": datetime.utcnow().isoformat()
        }

    async def start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks."""

        async def metrics_collection_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Collect metrics every 5 minutes

                    current_metrics = await self.get_current_metrics()
                    self.metrics_history.append(current_metrics)

                    # Keep last 24 hours of metrics (288 5-minute intervals)
                    if len(self.metrics_history) > 288:
                        self.metrics_history.pop(0)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Metrics collection error: {e}")

        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Health check every minute

                    health_status = await self.monitor.get_health_status()

                    # Check for critical issues
                    if health_status.status == HealthStatus.CRITICAL:
                        await self.audit_logger.log_event(AuditEvent(
                            event_type=AuditEventType.SECURITY_INCIDENT,
                            action="Critical system health detected",
                            severity=AuditSeverity.CRITICAL,
                            details=health_status.dict()
                        ))

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health check error: {e}")

        # Start background tasks
        self._metrics_task = asyncio.create_task(metrics_collection_loop())
        self._health_check_task = asyncio.create_task(health_check_loop())

        # Start component tasks
        await self.rate_limiter.start_cleanup_task()
        await self.monitor.start_monitoring()
        await self.sla_manager.start_monitoring()

        logger.info("Started enterprise API gateway background tasks")

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""

        # Cancel main tasks
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop component tasks
        await self.rate_limiter.stop_cleanup_task()
        await self.monitor.stop_monitoring()
        await self.sla_manager.stop_monitoring()

        logger.info("Stopped enterprise API gateway background tasks")

    def create_middleware(self) -> EnterpriseGatewayMiddleware:
        """Create middleware instance for FastAPI integration."""
        return EnterpriseGatewayMiddleware(None, self)


def create_enterprise_gateway(config_manager: EnterpriseConfigManager,
                            audit_logger: ComplianceAuditLogger,
                            rbac_manager: EnterpriseRBACManager) -> EnterpriseAPIGateway:
    """Factory function to create enterprise API gateway."""

    gateway = EnterpriseAPIGateway(config_manager, audit_logger, rbac_manager)

    logger.info("Created enterprise API gateway with comprehensive monitoring and compliance")

    return gateway


@asynccontextmanager
async def enterprise_gateway_lifespan(gateway: EnterpriseAPIGateway):
    """Lifespan context manager for enterprise gateway."""

    try:
        await gateway.start_background_tasks()
        yield gateway
    finally:
        await gateway.stop_background_tasks()
