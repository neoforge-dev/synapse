"""API versioning middleware integrating version management, deprecation, and transformation."""

import logging
import json
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .version_manager import APIVersionManager
from .deprecation import DeprecationManager
from .transformers import transformer_registry

logger = logging.getLogger(__name__)


class VersioningMiddleware(BaseHTTPMiddleware):
    """Comprehensive API versioning middleware.
    
    Features:
    - Automatic version detection from paths and headers
    - Deprecation warning injection
    - Request/response transformation between versions
    - Backward compatibility enforcement
    - Version routing and validation
    """
    
    def __init__(
        self,
        app,
        version_manager: Optional[APIVersionManager] = None,
        deprecation_manager: Optional[DeprecationManager] = None,
        enable_transformations: bool = True,
        enable_deprecation_warnings: bool = True
    ):
        """Initialize versioning middleware.
        
        Args:
            app: FastAPI application
            version_manager: API version manager instance
            deprecation_manager: Deprecation manager instance
            enable_transformations: Whether to enable data transformations
            enable_deprecation_warnings: Whether to add deprecation warnings
        """
        super().__init__(app)
        
        self.version_manager = version_manager or APIVersionManager()
        self.deprecation_manager = deprecation_manager or DeprecationManager()
        self.enable_transformations = enable_transformations
        self.enable_deprecation_warnings = enable_deprecation_warnings
        
        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'version_detections': {},
            'transformations_applied': 0,
            'deprecation_warnings_sent': 0,
            'unsupported_version_requests': 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through versioning pipeline.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response with versioning applied
        """
        self.stats['total_requests'] += 1
        
        try:
            # 1. Extract version information
            original_path = request.url.path
            headers = dict(request.headers)
            
            # Determine API version
            requested_version = self.version_manager.determine_version(original_path, headers)
            
            # Track version usage
            if requested_version not in self.stats['version_detections']:
                self.stats['version_detections'][requested_version] = 0
            self.stats['version_detections'][requested_version] += 1
            
            # 2. Validate version support
            if not self.version_manager.is_version_supported(requested_version):
                self.stats['unsupported_version_requests'] += 1
                return await self._handle_unsupported_version(requested_version)
            
            # 3. Handle path-based version routing
            detected_path_version, clean_path = self.version_manager.extract_version_from_path(original_path)
            if detected_path_version:
                # Rewrite request URL to remove version prefix
                # This allows the same endpoints to handle multiple versions
                request._url = request.url.replace(path=clean_path)
            
            # 4. Transform request data if needed
            if self.enable_transformations and hasattr(request, 'json'):
                await self._transform_request_data(request, requested_version)
            
            # 5. Add version context to request
            request.state.api_version = requested_version
            request.state.original_path = original_path
            
            # 6. Process request
            response = await call_next(request)
            
            # 7. Post-process response
            await self._post_process_response(
                response, 
                requested_version, 
                original_path,
                headers
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Versioning middleware error: {e}")
            # Fail gracefully - process request without versioning
            return await call_next(request)
    
    async def _handle_unsupported_version(self, version: str) -> JSONResponse:
        """Handle requests for unsupported API versions.
        
        Args:
            version: Requested unsupported version
            
        Returns:
            Error response with version information
        """
        supported_versions = self.version_manager.get_supported_versions()
        latest_stable = self.version_manager.get_latest_stable_version()
        
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unsupported API Version",
                "message": f"API version '{version}' is not supported",
                "error_code": "UNSUPPORTED_API_VERSION",
                "details": {
                    "requested_version": version,
                    "supported_versions": supported_versions,
                    "recommended_version": latest_stable,
                    "version_detection_help": {
                        "path_format": "/api/{version}/endpoint",
                        "header_format": "Accept: application/vnd.techleadautopilot.v1+json",
                        "alternative_header": "X-API-Version: v1"
                    }
                }
            },
            headers={
                "X-API-Supported-Versions": ", ".join(supported_versions),
                "X-API-Latest-Version": latest_stable or "v1"
            }
        )
    
    async def _transform_request_data(self, request: Request, target_version: str) -> None:
        """Transform request data for version compatibility.
        
        Args:
            request: HTTP request with potential JSON body
            target_version: Target API version
        """
        try:
            # Only transform if request has JSON body
            if request.headers.get('content-type', '').startswith('application/json'):
                # Get request body
                body = await request.body()
                if body:
                    request_data = json.loads(body.decode())
                    
                    # Determine client version (could be different from target)
                    client_version = self._extract_client_version(request) or target_version
                    
                    # Transform if versions differ
                    if client_version != target_version:
                        transformer = transformer_registry.get_request_transformer(
                            client_version, target_version
                        )
                        
                        if transformer:
                            transformed_data = transformer.transform(request_data)
                            
                            # Replace request body
                            new_body = json.dumps(transformed_data).encode()
                            request._body = new_body
                            request.headers['content-length'] = str(len(new_body))
                            
                            self.stats['transformations_applied'] += 1
                            
                            logger.debug(
                                f"Transformed request data from {client_version} to {target_version}"
                            )
                            
        except Exception as e:
            logger.error(f"Request transformation failed: {e}")
    
    def _extract_client_version(self, request: Request) -> Optional[str]:
        """Extract client API version preference from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Client's preferred API version
        """
        # Check custom client version headers
        client_version = (
            request.headers.get('x-client-api-version') or
            request.headers.get('x-api-version-preference')
        )
        
        if client_version and self.version_manager.is_version_supported(client_version):
            return client_version
        
        return None
    
    async def _post_process_response(
        self,
        response: Response,
        api_version: str,
        original_path: str,
        request_headers: Dict[str, str]
    ) -> None:
        """Post-process response with versioning features.
        
        Args:
            response: HTTP response
            api_version: API version used
            original_path: Original request path
            request_headers: Original request headers
        """
        # Add version headers
        self._add_version_headers(response, api_version)
        
        # Add deprecation warnings
        if self.enable_deprecation_warnings:
            await self._add_deprecation_warnings(response, api_version, original_path, request_headers)
        
        # Transform response data if needed
        if self.enable_transformations:
            await self._transform_response_data(response, api_version, request_headers)
    
    def _add_version_headers(self, response: Response, api_version: str) -> None:
        """Add version information headers to response.
        
        Args:
            response: HTTP response
            api_version: API version used
        """
        version_info = self.version_manager.get_version_info(api_version)
        
        response.headers.update({
            "X-API-Version": api_version,
            "X-API-Version-Status": version_info.status.value if version_info else "unknown",
            "X-API-Supported-Versions": ", ".join(self.version_manager.get_supported_versions())
        })
        
        # Add latest version info
        latest_stable = self.version_manager.get_latest_stable_version()
        if latest_stable:
            response.headers["X-API-Latest-Stable"] = latest_stable
        
        # Add version-specific headers
        if version_info and version_info.is_deprecated:
            response.headers["X-API-Deprecated"] = "true"
            if version_info.sunset_date:
                response.headers["X-API-Sunset-Date"] = version_info.sunset_date.isoformat()
    
    async def _add_deprecation_warnings(
        self,
        response: Response,
        api_version: str,
        original_path: str,
        request_headers: Dict[str, str]
    ) -> None:
        """Add deprecation warnings to response.
        
        Args:
            response: HTTP response
            api_version: API version used
            original_path: Original request path
            request_headers: Request headers
        """
        try:
            # Extract client ID for tracking (optional)
            client_id = (
                request_headers.get('x-client-id') or
                request_headers.get('user-agent', 'unknown')
            )
            
            # Get deprecation headers
            deprecation_headers = self.deprecation_manager.generate_deprecation_headers(
                original_path, api_version, client_id
            )
            
            if deprecation_headers:
                response.headers.update(deprecation_headers)
                self.stats['deprecation_warnings_sent'] += 1
            
            # Add deprecation warnings to JSON responses
            if (response.headers.get('content-type', '').startswith('application/json') and
                hasattr(response, 'body')):
                
                await self._inject_deprecation_warnings_to_json(
                    response, api_version, original_path
                )
                
        except Exception as e:
            logger.error(f"Failed to add deprecation warnings: {e}")
    
    async def _inject_deprecation_warnings_to_json(
        self,
        response: Response,
        api_version: str,
        original_path: str
    ) -> None:
        """Inject deprecation warnings into JSON response body.
        
        Args:
            response: HTTP response
            api_version: API version
            original_path: Request path
        """
        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            if body:
                response_data = json.loads(body.decode())
                
                # Generate deprecation warnings
                warnings = self.deprecation_manager.generate_response_warnings(
                    original_path, api_version
                )
                
                if warnings:
                    # Add warnings to response
                    if isinstance(response_data, dict):
                        response_data['_warnings'] = warnings
                    else:
                        # For non-dict responses, wrap in envelope
                        response_data = {
                            'data': response_data,
                            '_warnings': warnings
                        }
                    
                    # Update response body
                    new_body = json.dumps(response_data).encode()
                    
                    # Replace response
                    response.body = new_body
                    response.headers['content-length'] = str(len(new_body))
                    
        except Exception as e:
            logger.error(f"Failed to inject deprecation warnings to JSON: {e}")
    
    async def _transform_response_data(
        self,
        response: Response,
        api_version: str,
        request_headers: Dict[str, str]
    ) -> None:
        """Transform response data for client version compatibility.
        
        Args:
            response: HTTP response
            api_version: Server API version
            request_headers: Original request headers
        """
        try:
            # Check if client prefers different version
            client_version = self._extract_client_version_from_headers(request_headers)
            
            if (client_version and 
                client_version != api_version and
                response.headers.get('content-type', '').startswith('application/json')):
                
                # Get transformer
                transformer = transformer_registry.get_response_transformer(
                    api_version, client_version
                )
                
                if transformer:
                    # Get response body
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    if body:
                        response_data = json.loads(body.decode())
                        transformed_data = transformer.transform(response_data)
                        
                        # Update response
                        new_body = json.dumps(transformed_data).encode()
                        response.body = new_body
                        response.headers['content-length'] = str(len(new_body))
                        
                        # Add transformation headers
                        response.headers.update({
                            "X-API-Response-Transformed": "true",
                            "X-API-Transform-From": api_version,
                            "X-API-Transform-To": client_version
                        })
                        
                        self.stats['transformations_applied'] += 1
                        
                        logger.debug(
                            f"Transformed response from {api_version} to {client_version}"
                        )
                        
        except Exception as e:
            logger.error(f"Response transformation failed: {e}")
    
    def _extract_client_version_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract client version preference from headers.
        
        Args:
            headers: Request headers
            
        Returns:
            Client's preferred version
        """
        return (
            headers.get('x-client-api-version') or
            headers.get('x-api-version-preference') or
            headers.get('accept-version')
        )
    
    def get_versioning_stats(self) -> Dict[str, Any]:
        """Get comprehensive versioning statistics.
        
        Returns:
            Dictionary with versioning metrics
        """
        stats = dict(self.stats)
        
        # Add version manager stats
        stats.update(self.version_manager.get_version_stats())
        
        # Add deprecation stats
        deprecation_stats = self.deprecation_manager.get_deprecation_stats()
        stats.update({f"deprecation_{k}": v for k, v in deprecation_stats.items()})
        
        # Calculate percentages
        total = stats['total_requests']
        if total > 0:
            stats['transformation_rate'] = (stats['transformations_applied'] / total) * 100
            stats['deprecation_warning_rate'] = (stats['deprecation_warnings_sent'] / total) * 100
            stats['unsupported_version_rate'] = (stats['unsupported_version_requests'] / total) * 100
        
        return stats