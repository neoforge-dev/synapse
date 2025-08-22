"""
Authentication middleware for request processing.

Handles authentication context and user session management.
"""

import logging
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication context middleware.
    
    Adds authentication context to requests for logging and monitoring.
    Actual authentication is handled by dependencies in protected routes.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add authentication context to request state."""
        # Extract user context if available
        user_context = await self._extract_user_context(request)
        
        # Add to request state for logging and monitoring
        if user_context:
            request.state.user_id = user_context.get("user_id")
            request.state.organization_id = user_context.get("organization_id")
            request.state.user_role = user_context.get("role")
        
        response = await call_next(request)
        
        # Add user context to response headers (for debugging in development)
        if hasattr(request.state, "user_id") and request.state.user_id:
            response.headers["X-User-Context"] = "authenticated"
        
        return response
    
    async def _extract_user_context(self, request: Request) -> Optional[dict]:
        """Extract user context from JWT token if present."""
        try:
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            
            # Import here to avoid circular imports
            from ..auth.jwt import verify_token
            token_data = verify_token(token)
            
            if token_data:
                return {
                    "user_id": token_data.user_id,
                    "organization_id": token_data.organization_id,
                    "email": token_data.email,
                    "role": token_data.role
                }
            
        except Exception as e:
            logger.debug(f"Failed to extract user context: {e}")
        
        return None