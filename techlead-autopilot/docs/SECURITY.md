# Security Architecture

**TechLead AutoPilot** implements enterprise-grade security with multiple layers of protection, designed for production environments and compliance requirements.

## 🛡️ **Security Overview**

The platform uses a **defense-in-depth approach** with multiple security layers:

1. **Network Security** - TLS/SSL, HTTPS enforcement, WAF
2. **Application Security** - Multi-tier rate limiting, DDoS protection, input validation
3. **Authentication & Authorization** - JWT tokens, OAuth 2.0, role-based access
4. **Data Protection** - Encryption at rest/transit, PII sanitization, audit logging
5. **Infrastructure Security** - Container security, secrets management, monitoring

## 🔒 **Middleware Security Stack**

### 1. Rate Limiting & DDoS Protection

**Implementation**: `src/techlead_autopilot/infrastructure/security/rate_limiter.py` and `ddos_protection.py`

#### **Multi-Tier Rate Limiting**
- **Redis-backed sliding windows** for precise rate tracking
- **Burst allowance** for legitimate traffic spikes
- **Subscription-aware limits** based on user tier (Free/Pro/Enterprise)

```python
# Rate limit tiers
FREE_TIER = {
    "requests_per_hour": 1000,
    "content_generations_per_month": 50,
    "lead_queries_per_month": 100
}

PRO_TIER = {
    "requests_per_hour": 10000,
    "content_generations_per_month": 500,
    "lead_queries_per_month": 1000
}

ENTERPRISE_TIER = {
    "requests_per_hour": 100000,
    "content_generations_per_month": 5000,
    "lead_queries_per_month": 10000
}
```

#### **DDoS Protection Features**
- **Request pattern analysis** - Detects rapid requests, unusual endpoints, large payloads
- **Automatic IP blocking** - Temporary blocks for suspicious behavior
- **Connection limits** - Per-IP concurrent connection limits
- **Behavioral analysis** - Bot traffic detection and mitigation

#### **Response Headers**
```http
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

### 2. API Versioning & Deprecation Management

**Implementation**: `src/techlead_autopilot/infrastructure/versioning/version_manager.py`

#### **Version Detection Priority**
1. **Path-based versioning** - `/api/v1/`, `/api/v2/`
2. **Header-based versioning** - `Accept: application/vnd.api+json;version=1.1`
3. **Default version fallback** - Ensures compatibility

#### **Backward Compatibility**
- **Automatic data transformation** between API versions
- **Deprecation warnings** in response headers and body
- **Migration tools** for developers transitioning between versions

```http
Deprecation: true
Sunset: Wed, 31 Dec 2024 23:59:59 GMT
Deprecation-Info: "Use /api/v2/content instead. Migration guide: https://docs.techleadautopilot.com/migration/v1-to-v2"
```

### 3. Security Middleware

**Implementation**: `src/techlead_autopilot/api/middleware/security.py`

#### **Security Headers**
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: microphone=(), camera=(), geolocation=()
```

#### **Request Validation**
- **Content-Type enforcement** for POST/PUT requests
- **Request size limits** (10MB default, configurable)
- **Allowed methods validation** (GET, POST, PUT, DELETE, PATCH only)
- **Host header validation** against allowed domains

### 4. PII Sanitization

**Implementation**: `src/techlead_autopilot/api/middleware/security.py`

#### **Automatic PII Detection & Removal**
- **Email addresses** - Masked in logs and error responses
- **Phone numbers** - Pattern-based detection and sanitization
- **Credit card numbers** - Luhn algorithm validation and masking
- **Social Security Numbers** - Format detection and redaction

#### **Log Sanitization**
```python
# Example: Email sanitization
"user@example.com" → "u***@e***.com"

# Example: Phone sanitization  
"+1-555-123-4567" → "+1-***-***-4567"
```

### 5. Authentication Middleware

**Implementation**: `src/techlead_autopilot/api/middleware/auth.py`

#### **JWT Token Validation**
- **Signature verification** using HMAC SHA-256
- **Expiration checking** with configurable timeout
- **Issuer validation** to prevent token reuse
- **Scope-based authorization** for fine-grained permissions

#### **Session Management**
- **Refresh token rotation** for enhanced security
- **Device fingerprinting** for session validation
- **Concurrent session limits** per user account
- **Automatic logout** after inactivity

## 🔐 **Authentication & Authorization**

### JWT Token Structure

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "org_id": "organization_id",
  "scopes": ["content:read", "content:write", "leads:read"],
  "tier": "pro",
  "exp": 1640995200,
  "iat": 1640908800,
  "jti": "token_id"
}
```

### OAuth 2.0 Scopes

| Scope | Description | Access Level |
|-------|-------------|--------------|
| `content:read` | Read access to content data | Standard |
| `content:write` | Create and modify content | Elevated |
| `leads:read` | Read access to lead data | Standard |
| `leads:write` | Manage leads and notes | Elevated |
| `analytics:read` | Read access to analytics data | Standard |
| `user:profile` | Read user profile information | Standard |
| `admin` | Administrative access to all resources | Admin |

### Role-Based Access Control (RBAC)

#### **Organization Roles**
- **Owner** - Full access to organization settings and billing
- **Admin** - User management and feature configuration
- **Member** - Standard content generation and lead management
- **Viewer** - Read-only access to analytics and reports

## 🔍 **Security Monitoring**

### Audit Logging

**Implementation**: `src/techlead_autopilot/infrastructure/logging.py`

#### **Security Events Tracked**
- Authentication attempts (success/failure)
- Authorization failures (insufficient permissions)
- Rate limit violations and IP blocks
- Suspicious request patterns
- Configuration changes
- Data access and modifications

#### **Audit Log Format**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event": "security_event",
  "event_type": "authentication_failure", 
  "description": "Invalid credentials provided",
  "user_id": "user_123",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "request_id": "req_abc123",
  "severity": "medium"
}
```

### Real-time Alerting

#### **Security Alert Triggers**
- Multiple failed authentication attempts (5+ in 5 minutes)
- Rate limit violations exceeding threshold (100+ requests/minute)
- Suspicious request patterns detected
- Unauthorized access attempts to admin endpoints
- Unusual geographic login patterns
- Large data exports or bulk operations

#### **Alert Channels**
- **Slack/Discord** - Real-time notifications for critical events
- **Email** - Daily/weekly security summaries
- **Sentry** - Error tracking with security context
- **PagerDuty** - On-call escalation for critical incidents

## 🛠️ **Configuration**

### Environment Variables

#### **Core Security Settings**
```bash
# JWT Configuration
TECHLEAD_AUTOPILOT_SECRET_KEY=your-256-bit-secret-key
TECHLEAD_AUTOPILOT_ACCESS_TOKEN_EXPIRE_MINUTES=30
TECHLEAD_AUTOPILOT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
TECHLEAD_AUTOPILOT_ENABLE_RATE_LIMITING=true
TECHLEAD_AUTOPILOT_REDIS_URL=redis://localhost:6379

# Security Middleware
TECHLEAD_AUTOPILOT_ENABLE_SECURITY_MIDDLEWARE=true
TECHLEAD_AUTOPILOT_ENABLE_PII_SANITIZATION=true

# CORS Configuration
TECHLEAD_AUTOPILOT_ALLOWED_ORIGINS=https://app.techleadautopilot.com,https://techleadautopilot.com

# Monitoring
TECHLEAD_AUTOPILOT_SENTRY_DSN=your-sentry-dsn
TECHLEAD_AUTOPILOT_LOG_LEVEL=INFO
```

#### **Production Security Hardening**
```bash
# Enforce HTTPS
TECHLEAD_AUTOPILOT_FORCE_HTTPS=true

# Strict security headers
TECHLEAD_AUTOPILOT_SECURITY_HEADERS_STRICT=true

# Disable debug features
TECHLEAD_AUTOPILOT_DEBUG=false
TECHLEAD_AUTOPILOT_ENVIRONMENT=production

# Enhanced logging
TECHLEAD_AUTOPILOT_STRUCTURED_LOGGING=true
TECHLEAD_AUTOPILOT_LOG_FORMAT=json
```

## 🚨 **Incident Response**

### Security Incident Categories

#### **Critical (P0) - Immediate Response**
- Data breach or unauthorized data access
- System compromise or malicious code execution
- Complete service outage affecting all users
- Active attack in progress

#### **High (P1) - 1 Hour Response**
- Authentication bypass or privilege escalation
- Significant DDoS attack affecting service
- Security vulnerability in production code
- Suspicious admin account activity

#### **Medium (P2) - 4 Hour Response**
- Rate limiting failures or abuse
- Minor data exposure (non-PII)
- Configuration security issues
- Suspicious user behavior patterns

### Response Procedures

#### **Immediate Actions**
1. **Isolate affected systems** - Block malicious IPs, disable compromised accounts
2. **Assess impact** - Determine scope of data/system compromise
3. **Notify stakeholders** - Alert security team, management, affected users
4. **Preserve evidence** - Capture logs, network traffic, system state

#### **Investigation & Recovery**
1. **Root cause analysis** - Identify vulnerability or attack vector
2. **Patch vulnerabilities** - Deploy security fixes immediately
3. **Monitor for persistence** - Ensure attackers don't maintain access
4. **Document lessons learned** - Update procedures and defenses

## 📋 **Security Checklist**

### Production Deployment Security

#### **Pre-Deployment**
- [ ] Security headers configured and tested
- [ ] Rate limiting properly configured with Redis
- [ ] JWT secrets properly generated and secured
- [ ] HTTPS certificates valid and properly configured
- [ ] PII sanitization enabled and tested
- [ ] Audit logging configured with proper retention
- [ ] Security scanning completed (SAST, DAST, dependency scan)
- [ ] Penetration testing completed and issues resolved

#### **Post-Deployment**  
- [ ] Monitoring and alerting functioning correctly
- [ ] Security incident response procedures tested
- [ ] Backup and recovery procedures validated
- [ ] Access controls and permissions reviewed
- [ ] Third-party integrations security validated
- [ ] Documentation updated with security procedures

### Regular Security Maintenance

#### **Weekly**
- [ ] Review security alerts and audit logs
- [ ] Check for new CVEs affecting dependencies
- [ ] Validate backup integrity and recovery procedures
- [ ] Monitor rate limiting effectiveness and adjust thresholds

#### **Monthly**
- [ ] Review and update security configurations
- [ ] Conduct access reviews and permission audits
- [ ] Update security documentation and procedures
- [ ] Test incident response procedures
- [ ] Security training for development team

#### **Quarterly**
- [ ] Penetration testing or security assessment
- [ ] Review and update security policies
- [ ] Security architecture review and improvements
- [ ] Compliance audit (SOC 2, GDPR, etc.)
- [ ] Disaster recovery testing

## 🔗 **Security Resources**

### Documentation
- [OWASP Top 10 Web Application Security Risks](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

### Tools & Libraries
- **Bandit** - Python security linter
- **Safety** - Dependency vulnerability scanner  
- **Ruff** - Code quality and security checks
- **Sentry** - Error tracking and monitoring
- **Redis** - Session storage and rate limiting backend

### Compliance Standards
- **SOC 2 Type II** - Security and availability controls
- **GDPR** - Data protection and privacy compliance
- **CCPA** - California privacy regulations
- **ISO 27001** - Information security management standards

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Owner**: Security Team  
**Review Cycle**: Quarterly