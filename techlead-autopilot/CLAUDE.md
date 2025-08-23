# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the TechLead AutoPilot platform.

## Development Commands

### Setup and Installation
```bash
# Install dependencies using uv
uv sync --dev                       # Install all dependencies including dev tools
uv run pytest tests/test_simple.py # Run basic functionality tests
uv run uvicorn techlead_autopilot.api.main:create_app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Core business logic tests (good weather scenarios)
uv run pytest tests/test_simple.py -v --cov=src/techlead_autopilot

# All tests (including integration tests that may need setup)
uv run pytest tests/ -v

# Specific test categories
uv run pytest -m unit              # Unit tests only
uv run pytest -m integration       # Integration tests (may require external services)

# Test with coverage
uv run pytest tests/test_simple.py --cov=src/techlead_autopilot --cov-report=term-missing --cov-report=html
```

### Code Quality
```bash
# Lint code
uv run ruff check src/ tests/       # Check code style and errors
uv run mypy src/                    # Type checking

# Format code  
uv run ruff format src/ tests/      # Auto-format code
```

### Database Management
```bash
# Create new migration
uv run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
uv run alembic upgrade head

# Initialize database
uv run python scripts/init_db.py
```

## Project Architecture

TechLead AutoPilot is a **comprehensive SaaS platform** that automates technical leadership content generation and consultation lead detection. Built on proven algorithms that generated €290K in consultation pipeline value.

### Core Value Proposition
- **Content Generation Engine**: AI-powered LinkedIn content using proven €290K templates
- **Lead Detection System**: 85%+ accurate consultation opportunity detection with priority scoring  
- **Automated Posting**: Optimal timing strategies (6:30 AM Tue/Thu) for maximum engagement
- **Analytics & ROI**: Complete content-to-consultation attribution and business intelligence

### Technology Stack

**Backend Infrastructure** (`src/techlead_autopilot/`):
- **FastAPI**: Modern async web framework with automatic OpenAPI docs
- **SQLAlchemy + PostgreSQL**: Multi-tenant database with organization isolation
- **Redis**: Caching, sessions, and rate limiting backend
- **JWT Authentication**: Secure token-based auth with refresh mechanism

**Security & Infrastructure** (`infrastructure/`):
- **Multi-tier Rate Limiting**: IP, User, and Endpoint-based limits with Redis sliding windows
- **DDoS Protection**: Request pattern analysis and automatic IP blocking
- **API Versioning**: Full backward compatibility with automatic data transformation
- **Monitoring**: Structured logging, Sentry integration, health checks

**Frontend Application** (`frontend/`):
- **Next.js 14**: React with TypeScript and App Router
- **Tailwind CSS**: Modern responsive design system
- **Progressive Web App**: Offline support and mobile optimization
- **Real-time Updates**: WebSocket integration for live notifications

### Core Components

**API Layer** (`api/`):
- `main.py`: FastAPI application factory with middleware stack
- `routers/`: Modular API endpoints (auth, content, leads, scheduler, analytics)
- `auth/`: JWT authentication, password hashing, role-based access
- `middleware/`: Security, logging, rate limiting, error handling

**Business Logic** (`core/`):
- `content_generation/`: €290K proven content templates and generation engine
- `lead_detection/`: NLP-based consultation opportunity detection and scoring
- Technical knowledge base and content optimization algorithms

**Services** (`services/`):
- `ContentService`: Content generation, approval workflows, analytics
- `LeadService`: Lead detection, scoring, conversion tracking, notes
- `SchedulerService`: Optimal posting times, automation, LinkedIn integration

**Infrastructure** (`infrastructure/`):
- `database/`: SQLAlchemy models, session management, connection pooling
- `external_apis/`: LinkedIn OAuth and posting, third-party integrations
- `security/`: Rate limiting, DDoS protection, request analysis
- `versioning/`: API versioning, deprecation management, data transformation
- `documentation/`: Enhanced OpenAPI with interactive examples
- `logging.py`: Structured JSON logging with rotation
- `monitoring.py`: Sentry integration and error tracking

### Data Flow

1. **User Authentication**: JWT-based login with organization isolation
2. **Content Generation**: AI-powered content using proven templates
3. **Content Review**: Approval workflow with mobile-optimized interface
4. **Automated Posting**: LinkedIn integration with optimal timing (6:30 AM Tue/Thu)
5. **Lead Detection**: Real-time analysis of engagement for consultation opportunities
6. **Business Intelligence**: Complete analytics with content-to-consultation attribution

## Configuration

Environment variables use `TECHLEAD_AUTOPILOT_` or shorthand prefixes:

### Core Application
- `TECHLEAD_AUTOPILOT_SECRET_KEY`: JWT signing key
- `TECHLEAD_AUTOPILOT_ENVIRONMENT`: development, staging, production
- `TECHLEAD_AUTOPILOT_DEBUG`: Enable debug mode (default: false)

### Database & Caching  
- `TECHLEAD_AUTOPILOT_DATABASE_URL`: PostgreSQL connection string
- `TECHLEAD_AUTOPILOT_REDIS_URL`: Redis connection for caching and rate limiting

### External APIs
- `TECHLEAD_AUTOPILOT_OPENAI_API_KEY`: OpenAI for content generation
- `TECHLEAD_AUTOPILOT_LINKEDIN_CLIENT_ID/SECRET`: LinkedIn OAuth credentials
- `TECHLEAD_AUTOPILOT_STRIPE_SECRET_KEY`: Stripe for subscription billing

### Security & Monitoring
- `TECHLEAD_AUTOPILOT_SENTRY_DSN`: Error tracking and monitoring
- `TECHLEAD_AUTOPILOT_ENABLE_RATE_LIMITING`: Enable rate limiting (default: true)
- `TECHLEAD_AUTOPILOT_ENABLE_SECURITY_MIDDLEWARE`: Enable DDoS protection (default: true)

## Testing Strategy

**Test Organization**:
- `test_simple.py`: Core business logic tests (good weather scenarios) - **ALWAYS PASSING**
- `test_api_*.py`: API endpoint integration tests
- `test_services.py`: Service layer unit tests
- `test_integration.py`: Full workflow integration tests

**Test Markers** (pytest.ini):
- `unit`: Self-contained business logic tests
- `integration`: Tests requiring external services or database
- `auth`: Authentication and security tests
- `content`: Content generation tests
- `linkedin`: LinkedIn integration tests

**Critical Test Coverage**:
- Content generation algorithms: €290K proven templates
- Lead scoring accuracy: 85%+ detection rate validation
- Authentication flows: JWT, OAuth, role-based access
- Rate limiting: Multi-tier protection validation
- Analytics: ROI calculation and attribution accuracy

## Important Files

### Core Application
- `pyproject.toml`: Dependencies, project metadata, CLI entry point
- `src/techlead_autopilot/config/settings.py`: Centralized configuration management
- `src/techlead_autopilot/api/main.py`: FastAPI application factory with middleware
- `src/techlead_autopilot/infrastructure/database/models.py`: SQLAlchemy database models

### Development & Deployment
- `docker-compose.yml`: Local development services (PostgreSQL, Redis)
- `Dockerfile`: Production container image
- `alembic.ini`: Database migration configuration
- `scripts/init_db.py`: Database initialization script

### Documentation
- `docs/PLAN.md`: 4-epic development roadmap
- `docs/PROMPT.md`: Project handoff and continuation guide
- `STRATEGIC_ROADMAP.md`: 5-phase business development strategy

## Development Notes

### Technology Choices
- **uv**: Fast Python dependency management and virtual environments
- **SQLAlchemy 2.0**: Modern async database ORM with type safety
- **Pydantic v2**: Data validation with improved performance
- **Redis**: High-performance caching and rate limiting backend

### Architecture Patterns
- **Multi-tenant SaaS**: Organization-level data isolation and resource management
- **API-first design**: RESTful endpoints with comprehensive OpenAPI documentation  
- **Microservice-ready**: Modular services with clear boundaries and interfaces
- **Security-first**: Multiple protection layers (rate limiting, DDoS, input validation)

### Performance Optimizations
- **Database connection pooling**: Efficient resource management
- **Redis caching**: Sub-second response times for frequent queries
- **Async processing**: Non-blocking I/O for external API calls
- **CDN integration**: Static asset optimization and global distribution

## Business Context

### Proven Results
Based on €290K consultation pipeline generation:
- **Content Performance**: 3-5x higher engagement than industry average
- **Lead Detection**: 85%+ accuracy in identifying consultation opportunities
- **Conversion Rates**: 17% lead-to-consultation, 37.5% consultation-to-client
- **ROI**: 57:1+ LTV:CAC ratio across all subscription tiers

### Target Market
- **Primary**: Technical consultants, CTOs, VP Engineering
- **Secondary**: Engineering leadership coaches and consulting agencies
- **Enterprise**: Large organizations with technical thought leadership needs

### Subscription Tiers
- **Pro**: €297/month - Individual technical leaders
- **Agency**: €997/month - Consulting agencies and teams
- **Enterprise**: €2,997/month - Large organizations with custom needs

### Success Metrics
- **User Activation**: 90% complete onboarding within 7 days
- **Content Generation**: Users create 3+ posts per week using proven templates
- **Lead Generation**: 5+ qualified consultation inquiries per user per month  
- **Business Impact**: Measurable increase in consultation pipeline value

## Production Deployment

### Infrastructure Requirements
- **Application**: FastAPI on Docker containers (AWS ECS/GCP Cloud Run)
- **Database**: Managed PostgreSQL with read replicas
- **Caching**: Redis cluster for session storage and rate limiting
- **CDN**: CloudFlare for static assets and DDoS protection
- **Monitoring**: Sentry for error tracking, structured logs for debugging

### Security Hardening
- **Rate Limiting**: Multi-tier protection with Redis sliding windows
- **DDoS Protection**: Request pattern analysis and automatic blocking
- **Input Validation**: Multi-layer sanitization with PII protection
- **API Versioning**: Backward compatibility with automatic data transformation
- **Authentication**: JWT with refresh tokens, OAuth 2.0 integration

### Performance Targets
- **API Response Time**: <200ms for content operations, <500ms for analytics
- **Database Queries**: <50ms average, optimized with connection pooling
- **Security Middleware**: <50ms additional latency for protection features
- **Uptime**: 99.9% availability with health checks and auto-recovery

This platform represents a complete, production-ready SaaS solution for technical leadership automation, built on proven algorithms and enterprise-grade infrastructure.