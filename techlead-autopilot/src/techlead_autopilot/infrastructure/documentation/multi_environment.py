"""Multi-environment documentation support for OpenAPI specs."""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MultiEnvironmentDocumenter:
    """Provides multi-environment documentation support for OpenAPI specs.
    
    Supports different configurations for:
    - Development: Full documentation with debug features
    - Staging: Production-like documentation with staging endpoints
    - Production: Optimized documentation with security considerations
    """
    
    def __init__(self):
        """Initialize multi-environment documenter."""
        self.environment_configs = {
            "development": {
                "servers": [
                    {
                        "url": "http://localhost:8000",
                        "description": "Development server"
                    }
                ],
                "security_level": "debug",
                "show_internal_endpoints": True,
                "enable_try_it_out": True,
                "show_rate_limits": True,
                "include_examples": True
            },
            "staging": {
                "servers": [
                    {
                        "url": "https://staging-api.techleadautopilot.com",
                        "description": "Staging server"
                    }
                ],
                "security_level": "standard",
                "show_internal_endpoints": False,
                "enable_try_it_out": True,
                "show_rate_limits": True,
                "include_examples": True
            },
            "production": {
                "servers": [
                    {
                        "url": "https://api.techleadautopilot.com",
                        "description": "Production server"
                    }
                ],
                "security_level": "strict",
                "show_internal_endpoints": False,
                "enable_try_it_out": False,
                "show_rate_limits": True,
                "include_examples": False  # Reduce response size in production
            }
        }
    
    def enhance_for_environment(
        self, 
        schema: Dict[str, Any], 
        environment: str = "development"
    ) -> Dict[str, Any]:
        """Enhance OpenAPI schema for specific environment.
        
        Args:
            schema: Base OpenAPI schema
            environment: Target environment (development, staging, production)
            
        Returns:
            Enhanced schema for the target environment
        """
        if environment not in self.environment_configs:
            logger.warning(f"Unknown environment '{environment}', using development config")
            environment = "development"
        
        config = self.environment_configs[environment]
        
        # Update servers
        if config["servers"]:
            schema["servers"] = config["servers"]
        
        # Add environment-specific info
        if "info" not in schema:
            schema["info"] = {}
        
        schema["info"]["x-environment"] = {
            "name": environment,
            "security_level": config["security_level"],
            "features": {
                "try_it_out": config["enable_try_it_out"],
                "internal_endpoints": config["show_internal_endpoints"],
                "rate_limit_info": config["show_rate_limits"],
                "response_examples": config["include_examples"]
            }
        }
        
        # Environment-specific filtering
        if not config["show_internal_endpoints"]:
            self._filter_internal_endpoints(schema)
        
        if not config["include_examples"]:
            self._remove_examples(schema)
        
        # Add environment-specific security configurations
        self._enhance_security_for_environment(schema, environment, config)
        
        # Add environment-specific rate limiting
        self._enhance_rate_limiting_for_environment(schema, environment, config)
        
        return schema
    
    def _filter_internal_endpoints(self, schema: Dict[str, Any]) -> None:
        """Remove internal endpoints from schema."""
        if "paths" not in schema:
            return
        
        internal_patterns = [
            "/health/detailed",
            "/admin",
            "/internal",
            "/debug"
        ]
        
        paths_to_remove = []
        for path in schema["paths"]:
            for pattern in internal_patterns:
                if pattern in path:
                    paths_to_remove.append(path)
                    break
        
        for path in paths_to_remove:
            del schema["paths"][path]
            logger.debug(f"Removed internal endpoint: {path}")
    
    def _remove_examples(self, schema: Dict[str, Any]) -> None:
        """Remove examples from schema to reduce size."""
        if "paths" not in schema:
            return
        
        for path_item in schema["paths"].values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                
                # Remove request body examples
                if "requestBody" in operation:
                    request_body = operation["requestBody"]
                    if "content" in request_body:
                        for content in request_body["content"].values():
                            content.pop("examples", None)
                            content.pop("example", None)
                
                # Remove response examples
                if "responses" in operation:
                    for response in operation["responses"].values():
                        if "content" in response:
                            for content in response["content"].values():
                                content.pop("examples", None)
                                content.pop("example", None)
    
    def _enhance_security_for_environment(
        self, 
        schema: Dict[str, Any], 
        environment: str, 
        config: Dict[str, Any]
    ) -> None:
        """Add environment-specific security enhancements."""
        if "components" not in schema:
            schema["components"] = {}
        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}
        
        # Environment-specific security schemes
        if environment == "development":
            # Allow API key for development
            schema["components"]["securitySchemes"]["devApiKey"] = {
                "type": "apiKey",
                "in": "header",
                "name": "X-Dev-API-Key",
                "description": "Development API key for testing"
            }
        
        elif environment == "production":
            # Production security hardening
            if "info" not in schema:
                schema["info"] = {}
            
            schema["info"]["x-security"] = {
                "tls_required": True,
                "hsts_enabled": True,
                "csrf_protection": True,
                "rate_limiting": "strict",
                "ip_filtering": "enabled",
                "security_headers": [
                    "Strict-Transport-Security",
                    "Content-Security-Policy",
                    "X-Content-Type-Options",
                    "X-Frame-Options",
                    "X-XSS-Protection"
                ]
            }
    
    def _enhance_rate_limiting_for_environment(
        self, 
        schema: Dict[str, Any], 
        environment: str, 
        config: Dict[str, Any]
    ) -> None:
        """Add environment-specific rate limiting information."""
        if not config["show_rate_limits"]:
            return
        
        if "info" not in schema:
            schema["info"] = {}
        
        # Environment-specific rate limits
        rate_limits = {
            "development": {
                "description": "Relaxed rate limits for development",
                "limits": {
                    "requests_per_minute": 1000,
                    "content_generations_per_hour": 100,
                    "lead_queries_per_hour": 200
                }
            },
            "staging": {
                "description": "Production-like rate limits for testing",
                "limits": {
                    "requests_per_minute": 100,
                    "content_generations_per_hour": 50,
                    "lead_queries_per_hour": 100
                }
            },
            "production": {
                "description": "Strict rate limits based on subscription tier",
                "limits": {
                    "free_tier": {
                        "requests_per_minute": 20,
                        "content_generations_per_month": 50,
                        "lead_queries_per_month": 100
                    },
                    "pro_tier": {
                        "requests_per_minute": 100,
                        "content_generations_per_month": 500,
                        "lead_queries_per_month": 1000
                    },
                    "enterprise_tier": {
                        "requests_per_minute": 500,
                        "content_generations_per_month": 5000,
                        "lead_queries_per_month": 10000
                    }
                }
            }
        }
        
        if environment in rate_limits:
            schema["info"]["x-rateLimiting"] = rate_limits[environment]
    
    def get_environment_specific_ui_config(self, environment: str) -> Dict[str, Any]:
        """Get UI configuration for specific environment.
        
        Args:
            environment: Target environment
            
        Returns:
            UI configuration dictionary
        """
        if environment not in self.environment_configs:
            environment = "development"
        
        config = self.environment_configs[environment]
        
        ui_config = {
            "deepLinking": True,
            "displayRequestDuration": True,
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "docExpansion": "none" if environment == "production" else "list",
            "operationsSorter": "alpha",
            "tryItOutEnabled": config["enable_try_it_out"]
        }
        
        # Environment-specific UI tweaks
        if environment == "development":
            ui_config.update({
                "displayOperationId": True,
                "showMutatedRequest": True,
                "requestSnippetsEnabled": True
            })
        elif environment == "production":
            ui_config.update({
                "displayOperationId": False,
                "showMutatedRequest": False,
                "requestSnippetsEnabled": False,
                "docExpansion": "none"
            })
        
        return ui_config
    
    def get_supported_environments(self) -> List[str]:
        """Get list of supported environments.
        
        Returns:
            List of environment names
        """
        return list(self.environment_configs.keys())
    
    def validate_environment(self, environment: str) -> bool:
        """Validate if environment is supported.
        
        Args:
            environment: Environment name to validate
            
        Returns:
            True if environment is supported, False otherwise
        """
        return environment in self.environment_configs