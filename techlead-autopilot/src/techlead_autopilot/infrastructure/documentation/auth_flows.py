"""Authentication flow documentation generator for OpenAPI specs."""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AuthenticationFlowDocumenter:
    """Generates comprehensive authentication flow documentation for OpenAPI.
    
    Provides detailed documentation for:
    - JWT Bearer token authentication
    - OAuth 2.0 flows (Authorization Code, Client Credentials)
    - API key authentication
    - LinkedIn OAuth integration
    - Token refresh workflows
    """
    
    def __init__(self):
        """Initialize authentication flow documenter."""
        self.oauth_scopes = {
            "content:read": "Read access to content data",
            "content:write": "Create and modify content",
            "leads:read": "Read access to lead data", 
            "leads:write": "Manage leads and notes",
            "analytics:read": "Read access to analytics data",
            "user:profile": "Read user profile information",
            "admin": "Administrative access to all resources"
        }
    
    def generate_auth_components(self) -> Dict[str, Any]:
        """Generate authentication components for OpenAPI schema.
        
        Returns:
            Dictionary containing security schemes and components
        """
        return {
            "securitySchemes": self._generate_security_schemes(),
            "schemas": self._generate_auth_schemas()
        }
    
    def _generate_security_schemes(self) -> Dict[str, Any]:
        """Generate security schemes for different authentication methods."""
        return {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": """
JWT Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Lifetime**: 24 hours  
**Refresh**: Use `/auth/refresh` endpoint before expiration  
**Scopes**: Embedded in token payload

**Example Request**:
```bash
curl -X GET "https://api.techleadautopilot.com/api/v1/content" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```
""",
                "x-tokenEndpoint": "/api/v1/auth/token",
                "x-refreshEndpoint": "/api/v1/auth/refresh"
            },
            "oauth2": {
                "type": "oauth2",
                "description": """
OAuth 2.0 authentication with support for multiple flows.

**Supported Flows**:
- Authorization Code: For web applications
- Client Credentials: For server-to-server communication

**Token Scopes**: Control access to specific API features
**Token Lifetime**: 1 hour (access), 30 days (refresh)
""",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://api.techleadautopilot.com/oauth/authorize",
                        "tokenUrl": "https://api.techleadautopilot.com/oauth/token",
                        "refreshUrl": "https://api.techleadautopilot.com/oauth/refresh",
                        "scopes": self.oauth_scopes
                    },
                    "clientCredentials": {
                        "tokenUrl": "https://api.techleadautopilot.com/oauth/token",
                        "scopes": self.oauth_scopes
                    }
                },
                "x-pkceSupport": True,
                "x-examples": {
                    "authorizationCode": {
                        "step1": {
                            "description": "Redirect user to authorization URL",
                            "url": "https://api.techleadautopilot.com/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_CALLBACK&scope=content:read+leads:read&state=random_state"
                        },
                        "step2": {
                            "description": "Exchange authorization code for access token",
                            "curl": """
curl -X POST "https://api.techleadautopilot.com/oauth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=authorization_code&code=AUTH_CODE&redirect_uri=YOUR_CALLBACK&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
"""
                        }
                    },
                    "clientCredentials": {
                        "description": "Direct token request for server applications",
                        "curl": """
curl -X POST "https://api.techleadautopilot.com/oauth/token" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&scope=content:read+analytics:read"
"""
                    }
                }
            },
            "apiKey": {
                "type": "apiKey",
                "in": "header", 
                "name": "X-API-Key",
                "description": """
API Key authentication for server-side applications.

**Usage**: Include API key in X-API-Key header
**Limitations**: Read-only access, no user context
**Rate Limits**: Lower limits than OAuth tokens

**Example Request**:
```bash
curl -X GET "https://api.techleadautopilot.com/api/v1/analytics" \\
  -H "X-API-Key: YOUR_API_KEY"
```

**Security Note**: API keys should only be used server-side and never exposed in client-side code.
""",
                "x-keyManagement": {
                    "creation": "Generated in dashboard under API Keys section",
                    "rotation": "Recommended every 90 days",
                    "revocation": "Immediate via dashboard or API"
                }
            },
            "linkedinOAuth": {
                "type": "oauth2",
                "description": """
LinkedIn OAuth integration for posting content and accessing LinkedIn data.

**Required Scopes**: 
- `w_member_social`: Post content to LinkedIn
- `r_liteprofile`: Access basic profile information
- `r_emailaddress`: Access email address

**Integration Flow**:
1. User connects LinkedIn account via OAuth
2. TechLead AutoPilot stores encrypted tokens
3. Automated posting uses stored credentials
4. Users can revoke access anytime

**Rate Limits**: LinkedIn API limits apply (300 posts/day)
""",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://www.linkedin.com/oauth/v2/authorization",
                        "tokenUrl": "https://www.linkedin.com/oauth/v2/accessToken",
                        "scopes": {
                            "w_member_social": "Post updates to LinkedIn",
                            "r_liteprofile": "Read basic profile information",
                            "r_emailaddress": "Access email address"
                        }
                    }
                },
                "x-integration": {
                    "connectEndpoint": "/api/v1/integrations/linkedin/connect",
                    "statusEndpoint": "/api/v1/integrations/linkedin/status",
                    "disconnectEndpoint": "/api/v1/integrations/linkedin/disconnect"
                }
            }
        }
    
    def _generate_auth_schemas(self) -> Dict[str, Any]:
        """Generate authentication-related schemas."""
        return {
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User email address",
                        "example": "user@example.com"
                    },
                    "password": {
                        "type": "string",
                        "format": "password",
                        "minLength": 8,
                        "description": "User password (minimum 8 characters)",
                        "example": "SecurePassword123!"
                    },
                    "remember_me": {
                        "type": "boolean",
                        "default": False,
                        "description": "Extend token lifetime for trusted devices"
                    }
                },
                "example": {
                    "email": "user@example.com",
                    "password": "SecurePassword123!",
                    "remember_me": True
                }
            },
            "TokenResponse": {
                "type": "object",
                "properties": {
                    "access_token": {
                        "type": "string",
                        "description": "JWT access token",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    },
                    "token_type": {
                        "type": "string",
                        "enum": ["bearer"],
                        "description": "Token type (always 'bearer')",
                        "example": "bearer"
                    },
                    "expires_in": {
                        "type": "integer",
                        "description": "Token lifetime in seconds",
                        "example": 86400
                    },
                    "refresh_token": {
                        "type": "string",
                        "description": "Refresh token for obtaining new access tokens",
                        "example": "def50200..."
                    },
                    "scope": {
                        "type": "string",
                        "description": "Space-separated list of granted scopes",
                        "example": "content:read content:write leads:read"
                    },
                    "user": {
                        "$ref": "#/components/schemas/UserProfile"
                    }
                },
                "required": ["access_token", "token_type", "expires_in"]
            },
            "RefreshTokenRequest": {
                "type": "object",
                "required": ["refresh_token"],
                "properties": {
                    "refresh_token": {
                        "type": "string",
                        "description": "Valid refresh token",
                        "example": "def50200..."
                    },
                    "grant_type": {
                        "type": "string",
                        "enum": ["refresh_token"],
                        "default": "refresh_token",
                        "description": "OAuth grant type"
                    }
                }
            },
            "UserProfile": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Unique user identifier",
                        "example": "123e4567-e89b-12d3-a456-426614174000"
                    },
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "User email address",
                        "example": "user@example.com"
                    },
                    "name": {
                        "type": "string",
                        "description": "User full name",
                        "example": "John Doe"
                    },
                    "subscription_tier": {
                        "type": "string",
                        "enum": ["free", "pro", "enterprise"],
                        "description": "User subscription tier",
                        "example": "pro"
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Account creation timestamp",
                        "example": "2024-01-15T10:30:00Z"
                    },
                    "linkedin_connected": {
                        "type": "boolean",
                        "description": "Whether LinkedIn account is connected",
                        "example": True
                    }
                }
            },
            "AuthError": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error type",
                        "enum": [
                            "invalid_request",
                            "invalid_client", 
                            "invalid_grant",
                            "unauthorized_client",
                            "unsupported_grant_type",
                            "invalid_scope",
                            "authentication_failed",
                            "token_expired"
                        ]
                    },
                    "error_description": {
                        "type": "string",
                        "description": "Human-readable error description"
                    },
                    "error_code": {
                        "type": "string",
                        "description": "Application-specific error code"
                    },
                    "error_uri": {
                        "type": "string",
                        "format": "uri",
                        "description": "URI to documentation about the error"
                    }
                },
                "example": {
                    "error": "invalid_grant",
                    "error_description": "The provided authorization grant is invalid",
                    "error_code": "AUTH_INVALID_CREDENTIALS",
                    "error_uri": "https://docs.techleadautopilot.com/errors/auth"
                }
            },
            "LinkedInConnectionRequest": {
                "type": "object",
                "properties": {
                    "redirect_uri": {
                        "type": "string",
                        "format": "uri",
                        "description": "URI to redirect after LinkedIn authentication",
                        "example": "https://app.techleadautopilot.com/linkedin/callback"
                    },
                    "state": {
                        "type": "string",
                        "description": "Random state parameter for security",
                        "example": "random_secure_state_string"
                    }
                },
                "required": ["redirect_uri"]
            },
            "LinkedInConnectionStatus": {
                "type": "object",
                "properties": {
                    "connected": {
                        "type": "boolean",
                        "description": "Whether LinkedIn account is connected",
                        "example": True
                    },
                    "profile_name": {
                        "type": "string",
                        "description": "LinkedIn profile name",
                        "example": "John Doe"
                    },
                    "profile_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "LinkedIn profile URL",
                        "example": "https://www.linkedin.com/in/johndoe"
                    },
                    "connected_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "When account was connected",
                        "example": "2024-01-15T10:30:00Z"
                    },
                    "posting_enabled": {
                        "type": "boolean",
                        "description": "Whether automated posting is enabled",
                        "example": True
                    },
                    "last_post_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Timestamp of last automated post",
                        "example": "2024-01-20T14:15:00Z"
                    }
                }
            }
        }
    
    def generate_auth_examples(self) -> Dict[str, Any]:
        """Generate comprehensive authentication examples."""
        return {
            "jwt_authentication": {
                "login": {
                    "summary": "Login with email and password",
                    "description": "Exchange user credentials for JWT tokens",
                    "value": {
                        "email": "user@example.com",
                        "password": "SecurePassword123!",
                        "remember_me": True
                    }
                },
                "refresh": {
                    "summary": "Refresh access token",
                    "description": "Get new access token using refresh token",
                    "value": {
                        "refresh_token": "def502000a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
                        "grant_type": "refresh_token"
                    }
                }
            },
            "oauth2_flows": {
                "authorization_code": {
                    "summary": "Authorization Code Flow",
                    "description": "Full OAuth 2.0 flow for web applications",
                    "steps": [
                        {
                            "step": 1,
                            "description": "Redirect to authorization server",
                            "url": "https://api.techleadautopilot.com/oauth/authorize?response_type=code&client_id=your_client_id&redirect_uri=https://yourapp.com/callback&scope=content:read+leads:read&state=xyz123"
                        },
                        {
                            "step": 2,
                            "description": "Exchange code for tokens",
                            "request": {
                                "grant_type": "authorization_code",
                                "code": "received_authorization_code",
                                "redirect_uri": "https://yourapp.com/callback",
                                "client_id": "your_client_id",
                                "client_secret": "your_client_secret"
                            }
                        }
                    ]
                },
                "client_credentials": {
                    "summary": "Client Credentials Flow",
                    "description": "Server-to-server authentication",
                    "value": {
                        "grant_type": "client_credentials",
                        "client_id": "your_client_id",
                        "client_secret": "your_client_secret",
                        "scope": "content:read analytics:read"
                    }
                }
            },
            "linkedin_integration": {
                "connect": {
                    "summary": "Connect LinkedIn account",
                    "description": "Initiate LinkedIn OAuth connection",
                    "value": {
                        "redirect_uri": "https://app.techleadautopilot.com/linkedin/callback",
                        "state": "secure_random_state_12345"
                    }
                }
            }
        }
    
    def generate_auth_documentation(self) -> Dict[str, str]:
        """Generate detailed authentication documentation sections."""
        return {
            "overview": """
# Authentication Overview

TechLead AutoPilot API supports multiple authentication methods to accommodate different use cases:

## 🔐 Authentication Methods

1. **JWT Bearer Tokens** - Recommended for most applications
2. **OAuth 2.0** - For third-party integrations and advanced flows  
3. **API Keys** - For server-side read-only access
4. **LinkedIn OAuth** - For social media integrations

## 🚀 Quick Start

The fastest way to get started is with JWT authentication:

1. Register at https://app.techleadautopilot.com
2. Use `/api/v1/auth/login` to get tokens
3. Include `Authorization: Bearer <token>` in requests
4. Use `/api/v1/auth/refresh` before token expires

## 🔒 Security Best Practices

- **Never expose tokens** in client-side code or public repositories
- **Use HTTPS** for all authentication requests
- **Implement token refresh** to maintain long-running sessions
- **Store tokens securely** using proper encryption/storage
- **Rotate API keys regularly** (every 90 days recommended)
""",
            "jwt_guide": """
# JWT Authentication Guide

## Token Structure

JWT tokens contain three parts (header.payload.signature):

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature
```

## Token Payload

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "org_id": "organization_id", 
  "scopes": ["content:read", "content:write"],
  "tier": "pro",
  "exp": 1640995200,
  "iat": 1640908800
}
```

## Implementation Examples

### Python
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.techleadautopilot.com/api/v1/content",
    headers=headers
)
```

### JavaScript
```javascript
const response = await fetch('/api/v1/content', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});
```

### cURL
```bash
curl -H "Authorization: Bearer ${TOKEN}" \\
     -H "Content-Type: application/json" \\
     "https://api.techleadautopilot.com/api/v1/content"
```
""",
            "oauth_guide": """
# OAuth 2.0 Integration Guide

## Supported Flows

### Authorization Code Flow (Web Apps)
Best for web applications with server-side components.

**Step 1**: Redirect user to authorization server
```
GET /oauth/authorize?
    response_type=code&
    client_id=YOUR_CLIENT_ID&
    redirect_uri=YOUR_CALLBACK_URL&
    scope=content:read+leads:read&
    state=RANDOM_STATE
```

**Step 2**: Exchange code for tokens
```bash
curl -X POST /oauth/token \\
  -d "grant_type=authorization_code" \\
  -d "code=AUTHORIZATION_CODE" \\
  -d "redirect_uri=YOUR_CALLBACK_URL" \\
  -d "client_id=YOUR_CLIENT_ID" \\
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### Client Credentials Flow (Server Apps)
For server-to-server communication without user context.

```bash
curl -X POST /oauth/token \\
  -d "grant_type=client_credentials" \\
  -d "client_id=YOUR_CLIENT_ID" \\
  -d "client_secret=YOUR_CLIENT_SECRET" \\
  -d "scope=content:read+analytics:read"
```

## Scope Permissions

| Scope | Description |
|-------|-------------|
| `content:read` | Read access to content data |
| `content:write` | Create and modify content |
| `leads:read` | Read access to lead data |
| `leads:write` | Manage leads and notes |
| `analytics:read` | Read access to analytics |
| `user:profile` | Read user profile |
| `admin` | Full administrative access |
""",
            "linkedin_guide": """
# LinkedIn Integration Guide

## Overview

TechLead AutoPilot integrates with LinkedIn to automatically post your generated content and track engagement.

## Required LinkedIn App Permissions

- `w_member_social` - Post content to LinkedIn
- `r_liteprofile` - Access basic profile information  
- `r_emailaddress` - Access email address

## Integration Flow

### 1. Initiate Connection
```bash
POST /api/v1/integrations/linkedin/connect
{
  "redirect_uri": "https://yourapp.com/linkedin/callback",
  "state": "secure_random_string"
}
```

### 2. Handle Callback
After user authorizes, LinkedIn redirects to your callback URL with authorization code.

### 3. Check Connection Status
```bash
GET /api/v1/integrations/linkedin/status
```

### 4. Automated Posting
Once connected, TechLead AutoPilot can automatically post content to LinkedIn using optimal timing algorithms.

## Rate Limits

LinkedIn enforces the following limits:
- **Posts per day**: 300 posts
- **API requests**: 500 requests per day per user
- **Throttling**: Rate limiting during peak hours

## Best Practices

- **Post frequency**: 2-3 high-quality posts per week
- **Optimal timing**: Tuesday/Thursday 6:30 AM (proven engagement times)
- **Content length**: 1300-2000 characters for maximum engagement
- **Include hashtags**: 3-5 relevant hashtags per post
"""
        }