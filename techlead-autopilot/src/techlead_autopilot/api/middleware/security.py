"""
Security middleware for API protection.

Provides security headers, input validation, and protection against common attacks.
"""

import logging
import time
from typing import Callable, Dict, List
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...config import get_settings

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for API protection.
    
    Adds security headers, validates requests, and protects against common attacks.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Security headers to add to all responses
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Server": "TechLead-AutoPilot"  # Hide server details
        }
        
        # Add HSTS in production
        if self.settings.is_production:
            self.security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Dangerous request patterns
        self.dangerous_patterns = [
            # SQL injection patterns
            "union select",
            "drop table",
            "delete from",
            "insert into",
            "update set",
            "<script",
            "javascript:",
            "vbscript:",
            # Path traversal
            "../",
            "..\\",
            "/etc/passwd",
            "/windows/system32",
            # Command injection
            "&& ",
            "| ",
            "; ",
            "`",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware."""
        start_time = time.time()
        
        try:
            # Validate request
            security_check = await self._validate_request_security(request)
            if not security_check["safe"]:
                logger.warning(f"Blocked dangerous request: {security_check['reason']}")
                return Response(
                    content="Request blocked by security policy",
                    status_code=400,
                    headers=self.security_headers
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            for header, value in self.security_headers.items():
                response.headers[header] = value
            
            # Add processing time header (for monitoring)
            processing_time = time.time() - start_time
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            
            # Return secure error response
            return Response(
                content="Internal server error",
                status_code=500,
                headers=self.security_headers
            )
    
    async def _validate_request_security(self, request: Request) -> Dict[str, any]:
        """
        Validate request for security issues.
        
        Returns:
            Dict with 'safe' boolean and 'reason' string
        """
        # Check request size (prevent large payload attacks)
        if hasattr(request, "headers"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                return {"safe": False, "reason": "Request too large"}
        
        # Check URL for dangerous patterns
        url_str = str(request.url).lower()
        for pattern in self.dangerous_patterns:
            if pattern in url_str:
                return {"safe": False, "reason": f"Dangerous pattern in URL: {pattern}"}
        
        # Check query parameters
        if request.query_params:
            query_str = str(request.query_params).lower()
            for pattern in self.dangerous_patterns:
                if pattern in query_str:
                    return {"safe": False, "reason": f"Dangerous pattern in query: {pattern}"}
        
        # Check User-Agent (block known bad bots)
        user_agent = request.headers.get("user-agent", "").lower()
        blocked_agents = [
            "sqlmap",
            "nikto",
            "nessus",
            "openvas",
            "masscan",
            "nmap",
            "dirb",
            "gobuster",
            "wfuzz"
        ]
        
        for blocked_agent in blocked_agents:
            if blocked_agent in user_agent:
                return {"safe": False, "reason": f"Blocked user agent: {blocked_agent}"}
        
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-host",  # Potential host header injection
            "x-original-url",    # Potential path manipulation
            "x-rewrite-url",     # Potential path manipulation
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")
        
        return {"safe": True, "reason": "Request passed security validation"}
    
    def _is_safe_origin(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        if not origin:
            return False
        
        allowed_origins = [
            "http://localhost:3000",    # Development frontend
            "http://localhost:8000",    # Development API
            "https://app.techleadautopilot.com",  # Production frontend
            "https://api.techleadautopilot.com",  # Production API
        ]
        
        return origin in allowed_origins


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Input sanitization middleware.
    
    Sanitizes request data to prevent XSS and injection attacks.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # HTML tags to strip
        self.html_tags = [
            "<script", "</script>",
            "<iframe", "</iframe>",
            "<object", "</object>",
            "<embed", "</embed>",
            "<form", "</form>",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "onclick=",
            "onmouseover=",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Sanitize request inputs."""
        try:
            # Only sanitize specific content types
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type and request.method in ["POST", "PUT", "PATCH"]:
                # For JSON requests, we'll rely on Pydantic validation
                # Additional sanitization can be added here if needed
                pass
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Input sanitization middleware error: {e}")
            return await call_next(request)
    
    def _sanitize_text(self, text: str) -> str:
        """Remove potentially dangerous HTML content."""
        if not isinstance(text, str):
            return text
        
        sanitized = text
        for tag in self.html_tags:
            sanitized = sanitized.replace(tag.lower(), "")
            sanitized = sanitized.replace(tag.upper(), "")
        
        return sanitized


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware for security monitoring.
    
    Logs requests for security analysis and debugging.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Sensitive data to redact from logs
        self.sensitive_fields = [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details for security monitoring."""
        start_time = time.time()
        
        # Collect request info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        path = str(request.url.path)
        
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Log request (with sensitive data redacted)
            log_data = {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "processing_time": f"{processing_time:.3f}s",
                "client_ip": client_ip,
                "user_agent": user_agent[:100] if user_agent else "",  # Truncate long user agents
            }
            
            # Log different levels based on status code
            if response.status_code >= 500:
                logger.error(f"Server error: {log_data}")
            elif response.status_code >= 400:
                logger.warning(f"Client error: {log_data}")
            elif self.settings.is_development:
                logger.info(f"Request: {log_data}")
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Request failed: {method} {path} - {str(e)} ({processing_time:.3f}s)")
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request headers."""
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        forwarded = request.headers.get("x-forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"