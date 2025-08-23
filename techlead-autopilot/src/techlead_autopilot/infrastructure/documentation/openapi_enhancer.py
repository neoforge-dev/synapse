"""Enhanced OpenAPI documentation with interactive examples, authentication flows, and rich metadata."""

import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
    get_redoc_html
)

from .auth_flows import AuthenticationFlowDocumenter
from .examples import ExampleGenerator
from .multi_environment import MultiEnvironmentDocumenter

logger = logging.getLogger(__name__)


class OpenAPIEnhancer:
    """Enhanced OpenAPI documentation generator with comprehensive features.
    
    Features:
    - Interactive examples with real API responses
    - Authentication flow documentation
    - Multi-environment documentation (dev, staging, prod)
    - Code generation examples (Python, JavaScript, cURL)
    - Rate limiting and quota information
    - Deprecation warnings and migration guides
    - Custom styling and branding
    """
    
    def __init__(
        self,
        app: FastAPI,
        title: str = "TechLead AutoPilot API",
        version: str = "1.0.0",
        description: str = None,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        enable_auth_flows: bool = True,
        enable_examples: bool = True,
        enable_multi_env: bool = True
    ):
        """Initialize OpenAPI enhancer.
        
        Args:
            app: FastAPI application instance
            title: API documentation title
            version: API version
            description: API description
            docs_url: Swagger UI URL
            redoc_url: ReDoc URL
            enable_auth_flows: Whether to include authentication flows
            enable_examples: Whether to generate interactive examples
            enable_multi_env: Whether to support multi-environment docs
        """
        self.app = app
        self.title = title
        self.version = version
        self.description = description or self._get_default_description()
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        
        # Feature flags
        self.enable_auth_flows = enable_auth_flows
        self.enable_examples = enable_examples
        self.enable_multi_env = enable_multi_env
        
        # Component initializers
        self.auth_documenter = AuthenticationFlowDocumenter() if enable_auth_flows else None
        self.example_generator = ExampleGenerator() if enable_examples else None
        self.env_documenter = MultiEnvironmentDocumenter() if enable_multi_env else None
        
        # Enhanced documentation metadata
        self.contact_info = {
            "name": "TechLead AutoPilot Support",
            "email": "support@techleadautopilot.com",
            "url": "https://techleadautopilot.com/support"
        }
        
        self.license_info = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        self.servers = [
            {
                "url": "https://api.techleadautopilot.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.techleadautopilot.com", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ]
        
        # Custom tags with descriptions
        self.tags_metadata = [
            {
                "name": "Authentication",
                "description": "User authentication and authorization endpoints",
                "externalDocs": {
                    "description": "Authentication Guide",
                    "url": "https://docs.techleadautopilot.com/auth"
                }
            },
            {
                "name": "Content Generation",
                "description": "AI-powered LinkedIn content generation with proven templates",
                "externalDocs": {
                    "description": "Content Generation Guide",
                    "url": "https://docs.techleadautopilot.com/content-generation"
                }
            },
            {
                "name": "Lead Detection",
                "description": "Consultation opportunity detection and lead scoring",
                "externalDocs": {
                    "description": "Lead Detection Guide", 
                    "url": "https://docs.techleadautopilot.com/lead-detection"
                }
            },
            {
                "name": "Analytics",
                "description": "Performance analytics and ROI tracking",
                "externalDocs": {
                    "description": "Analytics Guide",
                    "url": "https://docs.techleadautopilot.com/analytics"
                }
            },
            {
                "name": "Scheduling",
                "description": "Automated content posting with optimal timing",
                "externalDocs": {
                    "description": "Scheduling Guide",
                    "url": "https://docs.techleadautopilot.com/scheduling"
                }
            }
        ]
    
    def _get_default_description(self) -> str:
        """Get default API description."""
        return """
# TechLead AutoPilot API

Transform your technical expertise into systematic business growth with AI-powered content generation and lead detection.

## Key Features

- **🚀 Content Generation**: AI-powered LinkedIn content using proven €290K templates
- **🎯 Lead Detection**: 85%+ accurate consultation opportunity detection
- **📊 Analytics**: Content-to-consultation attribution and ROI tracking  
- **⏰ Automation**: Optimal timing posting with proven engagement patterns
- **🔒 Enterprise Security**: Multi-tier rate limiting and security hardening

## Getting Started

1. **Register** for an account and choose your subscription tier
2. **Authenticate** using JWT tokens or OAuth 2.0
3. **Generate content** using our proven templates
4. **Track leads** with automated detection and scoring
5. **Analyze performance** with comprehensive analytics

## Rate Limits

- **Free Tier**: 1,000 requests/hour, 50 content generations/month
- **Pro Tier**: 10,000 requests/hour, 500 content generations/month  
- **Enterprise**: Custom limits based on your needs

## Support

- 📧 **Email**: support@techleadautopilot.com
- 📖 **Documentation**: https://docs.techleadautopilot.com
- 💬 **Community**: https://community.techleadautopilot.com
"""
    
    def enhance_openapi_schema(self) -> None:
        """Enhance the OpenAPI schema with additional metadata and features."""
        
        def custom_openapi():
            if self.app.openapi_schema:
                return self.app.openapi_schema
                
            # Generate base OpenAPI schema
            openapi_schema = get_openapi(
                title=self.title,
                version=self.version,
                description=self.description,
                routes=self.app.routes,
                servers=self.servers,
                tags=self.tags_metadata
            )
            
            # Add contact and license information
            openapi_schema["info"]["contact"] = self.contact_info
            openapi_schema["info"]["license"] = self.license_info
            
            # Add custom extensions
            openapi_schema["info"]["x-logo"] = {
                "url": "https://techleadautopilot.com/logo.png",
                "altText": "TechLead AutoPilot"
            }
            
            # Add authentication flows
            if self.auth_documenter:
                auth_components = self.auth_documenter.generate_auth_components()
                if "components" not in openapi_schema:
                    openapi_schema["components"] = {}
                openapi_schema["components"].update(auth_components)
            
            # Enhance paths with examples and additional metadata
            self._enhance_paths(openapi_schema)
            
            # Add rate limiting information
            self._add_rate_limiting_info(openapi_schema)
            
            # Add deprecation information
            self._add_deprecation_info(openapi_schema)
            
            # Add code examples
            self._add_code_examples(openapi_schema)
            
            # Multi-environment enhancements
            if self.env_documenter:
                openapi_schema = self.env_documenter.enhance_for_environment(
                    openapi_schema, "production"
                )
            
            self.app.openapi_schema = openapi_schema
            return self.app.openapi_schema
        
        self.app.openapi = custom_openapi
    
    def _enhance_paths(self, schema: Dict[str, Any]) -> None:
        """Enhance API paths with examples and metadata."""
        if "paths" not in schema:
            return
            
        for path, path_item in schema["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    self._enhance_operation(operation, path, method)
    
    def _enhance_operation(self, operation: Dict[str, Any], path: str, method: str) -> None:
        """Enhance individual operation with examples and metadata."""
        
        # Add rate limiting information to operation
        if "x-rateLimit" not in operation:
            rate_limits = self._get_rate_limits_for_endpoint(path)
            if rate_limits:
                operation["x-rateLimit"] = rate_limits
        
        # Add examples if enabled
        if self.example_generator:
            examples = self.example_generator.generate_examples(path, method, operation)
            
            # Add request examples
            if examples.get("request") and "requestBody" in operation:
                if "content" in operation["requestBody"]:
                    for content_type, content in operation["requestBody"]["content"].items():
                        if "examples" not in content:
                            content["examples"] = {}
                        content["examples"].update(examples["request"])
            
            # Add response examples  
            if examples.get("responses") and "responses" in operation:
                for status_code, response_examples in examples["responses"].items():
                    if status_code in operation["responses"]:
                        response = operation["responses"][status_code]
                        if "content" in response:
                            for content_type, content in response["content"].items():
                                if "examples" not in content:
                                    content["examples"] = {}
                                content["examples"].update(response_examples)
        
        # Add detailed descriptions
        self._enhance_operation_description(operation, path, method)
        
        # Add common error responses if not present
        self._add_common_error_responses(operation)
    
    def _enhance_operation_description(self, operation: Dict[str, Any], path: str, method: str) -> None:
        """Enhance operation description with detailed information."""
        
        base_description = operation.get("description", "")
        
        # Add method-specific guidance
        method_guidance = {
            "get": "Retrieves data without side effects. Supports filtering, pagination, and sorting.",
            "post": "Creates new resources. Request body contains the resource data.",
            "put": "Updates existing resources. Full resource replacement.",
            "patch": "Partially updates existing resources. Only specified fields are updated.",
            "delete": "Removes resources. This operation cannot be undone."
        }
        
        if method in method_guidance:
            base_description += f"\n\n**Operation**: {method_guidance[method]}"
        
        # Add authentication requirements
        if "security" in operation:
            base_description += "\n\n**Authentication**: Required. Use Bearer token in Authorization header."
        
        # Add rate limiting info
        rate_limits = self._get_rate_limits_for_endpoint(path)
        if rate_limits:
            base_description += f"\n\n**Rate Limits**: {rate_limits.get('description', 'See rate limiting documentation')}"
        
        operation["description"] = base_description
    
    def _add_common_error_responses(self, operation: Dict[str, Any]) -> None:
        """Add common error responses to operation."""
        if "responses" not in operation:
            operation["responses"] = {}
        
        common_errors = {
            "400": {
                "description": "Bad Request - Invalid request parameters or body",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"},
                                "error_code": {"type": "string"},
                                "details": {"type": "object"}
                            }
                        },
                        "example": {
                            "error": "Validation Error",
                            "message": "Invalid request parameters",
                            "error_code": "VALIDATION_ERROR",
                            "details": {"field": "topic", "issue": "required"}
                        }
                    }
                }
            },
            "401": {
                "description": "Unauthorized - Authentication required or invalid",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"},
                                "error_code": {"type": "string"}
                            }
                        },
                        "example": {
                            "error": "Unauthorized",
                            "message": "Invalid or expired token",
                            "error_code": "UNAUTHORIZED"
                        }
                    }
                }
            },
            "403": {
                "description": "Forbidden - Insufficient permissions",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"},
                                "error_code": {"type": "string"}
                            }
                        },
                        "example": {
                            "error": "Forbidden",
                            "message": "Insufficient permissions for this operation",
                            "error_code": "FORBIDDEN"
                        }
                    }
                }
            },
            "429": {
                "description": "Too Many Requests - Rate limit exceeded",
                "headers": {
                    "X-RateLimit-Remaining": {
                        "description": "Number of requests remaining in current window",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Reset": {
                        "description": "Time when rate limit window resets",
                        "schema": {"type": "integer"}
                    },
                    "Retry-After": {
                        "description": "Seconds to wait before retrying",
                        "schema": {"type": "integer"}
                    }
                },
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"},
                                "error_code": {"type": "string"},
                                "retry_after": {"type": "integer"}
                            }
                        },
                        "example": {
                            "error": "Rate Limit Exceeded",
                            "message": "Too many requests. Please wait before retrying.",
                            "error_code": "RATE_LIMIT_EXCEEDED",
                            "retry_after": 60
                        }
                    }
                }
            },
            "500": {
                "description": "Internal Server Error - Unexpected server error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"},
                                "error_code": {"type": "string"},
                                "trace_id": {"type": "string"}
                            }
                        },
                        "example": {
                            "error": "Internal Server Error",
                            "message": "An unexpected error occurred",
                            "error_code": "INTERNAL_ERROR",
                            "trace_id": "abc123-def456-ghi789"
                        }
                    }
                }
            }
        }
        
        # Only add errors that don't already exist
        for status_code, error_response in common_errors.items():
            if status_code not in operation["responses"]:
                operation["responses"][status_code] = error_response
    
    def _get_rate_limits_for_endpoint(self, path: str) -> Optional[Dict[str, Any]]:
        """Get rate limiting information for specific endpoint."""
        
        # Map of endpoint patterns to rate limits
        rate_limit_map = {
            "/api/v1/content/generate": {
                "description": "10 requests/minute for free tier, 50/minute for pro",
                "limits": {
                    "free": {"requests_per_minute": 10},
                    "pro": {"requests_per_minute": 50},
                    "enterprise": {"requests_per_minute": 200}
                }
            },
            "/api/v1/leads": {
                "description": "20 requests/minute for all tiers",
                "limits": {
                    "free": {"requests_per_minute": 20},
                    "pro": {"requests_per_minute": 100},
                    "enterprise": {"requests_per_minute": 500}
                }
            },
            "/api/v1/analytics": {
                "description": "5 requests/minute for heavy reports",
                "limits": {
                    "free": {"requests_per_minute": 5},
                    "pro": {"requests_per_minute": 20},
                    "enterprise": {"requests_per_minute": 100}
                }
            }
        }
        
        for pattern, rate_info in rate_limit_map.items():
            if pattern in path:
                return rate_info
        
        return None
    
    def _add_rate_limiting_info(self, schema: Dict[str, Any]) -> None:
        """Add global rate limiting information to schema."""
        if "info" not in schema:
            schema["info"] = {}
        
        schema["info"]["x-rateLimiting"] = {
            "description": "API requests are rate limited based on subscription tier",
            "tiers": {
                "free": {
                    "requests_per_hour": 1000,
                    "content_generations_per_month": 50,
                    "lead_queries_per_month": 100
                },
                "pro": {
                    "requests_per_hour": 10000,
                    "content_generations_per_month": 500,
                    "lead_queries_per_month": 1000
                },
                "enterprise": {
                    "requests_per_hour": 100000,
                    "content_generations_per_month": 5000,
                    "lead_queries_per_month": 10000
                }
            },
            "headers": {
                "X-RateLimit-Remaining": "Number of requests remaining in current window",
                "X-RateLimit-Reset": "Time when rate limit window resets",
                "Retry-After": "Seconds to wait before retrying (on 429 responses)"
            }
        }
    
    def _add_deprecation_info(self, schema: Dict[str, Any]) -> None:
        """Add deprecation information to schema."""
        if "info" not in schema:
            schema["info"] = {}
        
        schema["info"]["x-deprecation"] = {
            "policy": "Features are deprecated with 90 days notice",
            "current_deprecations": [
                {
                    "feature": "v1 analytics endpoint",
                    "deprecated_since": "2024-01-15",
                    "sunset_date": "2024-12-31",
                    "replacement": "/api/v2/analytics",
                    "migration_guide": "https://docs.techleadautopilot.com/migration/analytics-v1-to-v2"
                }
            ],
            "notification_methods": [
                "HTTP headers (Deprecation, Sunset)",
                "Response warnings (_warnings field)",
                "Email notifications to registered developers",
                "Documentation updates"
            ]
        }
    
    def _add_code_examples(self, schema: Dict[str, Any]) -> None:
        """Add code examples to schema."""
        if "info" not in schema:
            schema["info"] = {}
        
        schema["info"]["x-code-samples"] = [
            {
                "lang": "Python",
                "label": "Python SDK",
                "source": """
import techlead_autopilot

client = techlead_autopilot.Client(api_token="your_token_here")

# Generate content
content = client.content.generate(
    topic="Leadership in Tech",
    content_type="thought_leadership"
)

# Detect leads
leads = client.leads.detect(content_id=content.id)
"""
            },
            {
                "lang": "JavaScript",
                "label": "JavaScript/Node.js",
                "source": """
const TechLeadAutoPilot = require('@techleadautopilot/sdk');

const client = new TechLeadAutoPilot({
  apiToken: 'your_token_here'
});

// Generate content
const content = await client.content.generate({
  topic: 'Leadership in Tech',
  contentType: 'thought_leadership'
});

// Detect leads  
const leads = await client.leads.detect(content.id);
"""
            },
            {
                "lang": "Shell",
                "label": "cURL",
                "source": """
# Generate content
curl -X POST "https://api.techleadautopilot.com/api/v1/content/generate" \\
  -H "Authorization: Bearer your_token_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "topic": "Leadership in Tech",
    "content_type": "thought_leadership"
  }'
"""
            }
        ]
    
    def setup_custom_docs_routes(self) -> None:
        """Set up custom documentation routes with enhanced UI."""
        
        @self.app.get(self.docs_url, include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url=self.app.openapi_url,
                title=f"{self.title} - Interactive API Documentation",
                oauth2_redirect_url=self.app.swagger_ui_oauth2_redirect_url,
                swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
                swagger_ui_parameters={
                    "deepLinking": True,
                    "displayRequestDuration": True,
                    "docExpansion": "none",
                    "operationsSorter": "alpha",
                    "filter": True,
                    "showExtensions": True,
                    "showCommonExtensions": True,
                    "tryItOutEnabled": True
                }
            )
        
        @self.app.get(f"{self.docs_url}/oauth2-redirect", include_in_schema=False)
        async def swagger_ui_redirect():
            return get_swagger_ui_oauth2_redirect_html()
        
        @self.app.get(self.redoc_url, include_in_schema=False)
        async def redoc_html():
            return get_redoc_html(
                openapi_url=self.app.openapi_url,
                title=f"{self.title} - API Reference",
                redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js"
            )
    
    def generate_static_documentation(self, output_dir: str = "docs") -> None:
        """Generate static documentation files.
        
        Args:
            output_dir: Directory to save static documentation
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate OpenAPI spec file
        openapi_spec = self.app.openapi()
        
        import json
        with open(output_path / "openapi.json", "w") as f:
            json.dump(openapi_spec, f, indent=2)
        
        logger.info(f"Generated static documentation in {output_dir}")
    
    def get_documentation_stats(self) -> Dict[str, Any]:
        """Get documentation statistics and coverage metrics.
        
        Returns:
            Dictionary with documentation statistics
        """
        openapi_spec = self.app.openapi()
        
        stats = {
            "total_paths": len(openapi_spec.get("paths", {})),
            "documented_paths": 0,
            "paths_with_examples": 0,
            "paths_with_rate_limits": 0,
            "authentication_schemes": len(
                openapi_spec.get("components", {}).get("securitySchemes", {})
            ),
            "total_operations": 0,
            "documented_operations": 0
        }
        
        for path_item in openapi_spec.get("paths", {}).values():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    stats["total_operations"] += 1
                    
                    if operation.get("description"):
                        stats["documented_operations"] += 1
                    
                    if operation.get("x-rateLimit"):
                        stats["paths_with_rate_limits"] += 1
                    
                    # Check for examples
                    has_examples = False
                    if "requestBody" in operation:
                        for content in operation["requestBody"].get("content", {}).values():
                            if content.get("examples"):
                                has_examples = True
                                break
                    
                    if "responses" in operation:
                        for response in operation["responses"].values():
                            for content in response.get("content", {}).values():
                                if content.get("examples"):
                                    has_examples = True
                                    break
                    
                    if has_examples:
                        stats["paths_with_examples"] += 1
        
        # Calculate coverage percentages
        if stats["total_operations"] > 0:
            stats["documentation_coverage"] = (
                stats["documented_operations"] / stats["total_operations"]
            ) * 100
            stats["example_coverage"] = (
                stats["paths_with_examples"] / stats["total_operations"]
            ) * 100
        
        return stats