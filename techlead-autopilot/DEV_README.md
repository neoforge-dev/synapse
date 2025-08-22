# TechLead AutoPilot - Development Guide

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd techlead-autopilot
make setup

# 2. Start services
make start-services

# 3. Run migrations  
make migrate

# 4. Start development server
make dev
```

Visit: http://localhost:8000/docs

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- uv (Python package manager)

### Install uv

```bash
pip install uv
```

## 🏗️ Project Structure

```
techlead-autopilot/
├── docs/                          # Business documentation (12 core docs)
├── src/techlead_autopilot/        # Main application code
│   ├── api/                       # FastAPI application
│   │   ├── auth/                  # Authentication logic
│   │   ├── middleware/            # Security & middleware
│   │   └── routers/              # API endpoints
│   ├── core/                     # Core business logic
│   │   ├── content_generation/   # Content generation engine
│   │   └── lead_detection/       # Lead detection algorithms
│   ├── infrastructure/           # External integrations
│   │   ├── database/             # Database models & session
│   │   └── external_apis/        # LinkedIn, OpenAI, Stripe
│   └── services/                 # Business services
├── migrations/                   # Database migrations
├── tests/                       # Test suite
├── scripts/                     # Development scripts
└── deploy/                     # Deployment configurations
```

## 🛠️ Development Commands

### Setup & Environment

| Command | Description |
|---------|-------------|
| `make setup` | Complete development environment setup |
| `make install` | Install dependencies only |
| `make start-services` | Start PostgreSQL & Redis |
| `make stop-services` | Stop development services |

### Development Server

| Command | Description |
|---------|-------------|
| `make dev` | Start development server with hot reload |
| `make up` | Start all services with Docker Compose |
| `make down` | Stop all services |
| `make logs` | View service logs |

### Database Operations

| Command | Description |
|---------|-------------|
| `make migrate` | Run database migrations |
| `make migration msg="description"` | Create new migration |
| `make db-reset` | ⚠️  Reset database (destroys data) |
| `make db-shell` | Open database shell |

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-coverage` | Run tests with coverage report |

### Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run linting and formatting |
| `make format` | Format code with ruff |
| `make check` | Check code without formatting |
| `make security` | Run security scans |

### Workflows

| Command | Description |
|---------|-------------|
| `make quick-start` | Setup + start services + migrate |
| `make ci` | Run all CI checks locally |
| `make fix` | Fix formatting and linting issues |
| `make clean` | Clean up generated files |

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key configurations:

- **Database**: `TECHLEAD_DATABASE_URL`
- **Redis**: `TECHLEAD_REDIS_URL`
- **Security**: `TECHLEAD_JWT_SECRET_KEY`
- **LinkedIn API**: `TECHLEAD_LINKEDIN_CLIENT_ID`, `TECHLEAD_LINKEDIN_CLIENT_SECRET`
- **OpenAI**: `TECHLEAD_OPENAI_API_KEY`
- **Stripe**: `TECHLEAD_STRIPE_SECRET_KEY`

### Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| `TECHLEAD_ENVIRONMENT` | `development` | `production` |
| `TECHLEAD_DEBUG` | `true` | `false` |
| `TECHLEAD_LOG_LEVEL` | `DEBUG` | `INFO` |
| `TECHLEAD_ENABLE_DOCS` | `true` | `false` |

## 🧪 Testing Strategy

### Test Types

```bash
# Unit tests - Fast, isolated
make test-unit

# Integration tests - With database
make test-integration  

# Coverage report
make test-coverage
```

### Writing Tests

```python
# Unit test example
def test_content_generation():
    engine = ContentGenerationEngine()
    content = engine.generate_content(
        content_type=ContentType.LINKEDIN_POST,
        topic="AI leadership"
    )
    assert content.engagement_score > 0.8

# Integration test example  
@pytest.mark.asyncio
async def test_user_registration_flow():
    async with AsyncClient(app=app) as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePassword123"
        })
    assert response.status_code == 201
```

## 🔐 Security Development

### Authentication Flow

1. **Registration**: Email + password → JWT tokens
2. **Login**: Email + password → Access + refresh tokens  
3. **Protected Routes**: Bearer token validation
4. **Token Refresh**: Refresh token → New access token

### Security Middleware Stack

1. **Error Handling**: Catches and sanitizes errors
2. **PII Sanitization**: Removes sensitive data from logs
3. **Request Logging**: Logs requests with user context
4. **Rate Limiting**: Prevents abuse (100 req/min general)
5. **Security Headers**: HSTS, CSP, XSS protection
6. **Authentication**: JWT validation context

### Security Testing

```bash
# Run security scans
make security

# Check for vulnerabilities
make audit
```

## 🐳 Docker Development

### Services

- **postgres**: Database on port 5432
- **redis**: Cache/rate limiting on port 6379  
- **api**: Application on port 8000
- **adminer**: Database admin on port 8080

### Docker Commands

```bash
# Start all services
make up

# View logs
make logs

# Rebuild API service
docker-compose build api

# Shell into API container
docker-compose exec api bash
```

## 📊 Database Development

### Schema Design

- **Multi-tenant**: Organization-based isolation
- **Relationships**: Users → Organizations → Content → Leads
- **Indexes**: Performance-optimized queries
- **Constraints**: Data integrity enforcement

### Migration Workflow

```bash
# Create migration
make migration msg="add user preferences table"

# Review generated migration
vim migrations/versions/xxx_add_user_preferences_table.py

# Apply migration
make migrate

# Rollback if needed
uv run alembic downgrade -1
```

## 🚀 Business Logic Development

### Content Generation Engine

Located in `src/techlead_autopilot/core/content_generation/`

- **Templates**: 8 proven content types
- **Knowledge Base**: Technical leadership insights
- **Engagement Prediction**: ML-based scoring

### Lead Detection System

Located in `src/techlead_autopilot/core/lead_detection/`

- **NLP Analysis**: 85%+ accuracy consultation detection
- **Scoring**: Multi-tier lead value estimation  
- **Priority**: €10K-€75K opportunity classification

## 🔗 API Development

### FastAPI Structure

```python
# Router example
@router.post("/content/generate")
async def generate_content(
    request: ContentGenerationRequest,
    current_user: User = Depends(get_current_user),
    content_service: ContentService = Depends()
):
    return await content_service.generate_content(request, current_user)
```

### Authentication Dependencies

```python
# Require authentication
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # JWT validation logic

# Organization isolation  
async def get_current_organization(user: User = Depends(get_current_user)):
    # Multi-tenant access control
```

## 📈 Performance Development

### Database Optimization

- **Connection Pooling**: SQLAlchemy async pool
- **Query Optimization**: Selective loading, indexes
- **Caching**: Redis for frequently accessed data

### Rate Limiting

- **Sliding Window**: Memory-based (Redis in production)
- **Adaptive**: Reduces limits under high load
- **Category-Based**: Different limits per endpoint type

## 🔧 Troubleshooting

### Common Issues

#### uv installation fails
```bash
# Install uv via pip
pip install uv

# Or use official installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Database connection errors
```bash
# Check if PostgreSQL is running
make start-services

# Reset database
make db-reset
```

#### Authentication tests failing  
```bash
# Check transformers version compatibility
uv pip install "transformers>=4.30.0,<4.35.0"
```

### Debug Mode

```bash
# Enable debug logging
export TECHLEAD_LOG_LEVEL=DEBUG

# Disable security middleware for testing
export TECHLEAD_ENABLE_RATE_LIMITING=false
```

## 📝 Contributing

### Code Standards

- **Formatting**: Ruff (automatic)
- **Linting**: Ruff + MyPy
- **Testing**: Pytest with 85%+ coverage
- **Security**: Bandit + Safety scans

### Pull Request Process

1. Create feature branch
2. Run `make ci` (linting, security, tests)
3. Commit with conventional commits
4. Open PR with comprehensive description
5. Ensure CI pipeline passes

### Commit Messages

```
feat: add LinkedIn content scheduling
fix: resolve authentication token refresh
docs: update API documentation
test: add integration tests for lead detection
```

## 🏃‍♂️ Sprint Development

### Current Sprint: Sprint 1 ✅ COMPLETED

**Goals**: Foundation infrastructure for MVP
- [x] Multi-tenant database schema
- [x] JWT authentication system  
- [x] Security middleware stack
- [x] Development environment setup

### Next Sprint: Sprint 2

**Goals**: Core business functionality
- [ ] Content Generation Engine implementation
- [ ] LinkedIn API integration
- [ ] Basic lead detection system
- [ ] User dashboard MVP

## 📚 Resources

- **API Documentation**: http://localhost:8000/docs
- **Database Admin**: http://localhost:8080 (adminer)
- **Business Documents**: `docs/` directory
- **Architecture Decisions**: `docs/04_technical_architecture.md`