# TechLead AutoPilot

Technical Leadership Automation Platform - Transform expertise into systematic business growth.

## Overview

TechLead AutoPilot is a SaaS platform that automates technical leadership content generation and lead detection for CTOs, VP Engineering, and technical consultants. Built on proven algorithms that generated €290K in consultation pipeline.

## Key Features

### ✅ MVP Foundation (Current)
- **Content Generation Engine**: AI-powered technical leadership content using proven templates
- **Lead Detection System**: 85%+ accurate consultation opportunity detection
- **Multi-tenant Architecture**: Scalable SaaS platform with organization isolation
- **API-First Design**: RESTful API with FastAPI and comprehensive documentation

### 🚧 Development Roadmap
- **LinkedIn Integration**: OAuth and automated posting
- **User Authentication**: JWT-based auth with role management
- **Billing Integration**: Stripe subscription management
- **Analytics Dashboard**: Performance tracking and ROI attribution
- **Mobile Optimization**: Content approval workflows

## Architecture

Built with modern, scalable technologies:

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL
- **Content Engine**: Proven algorithms from €290K pipeline
- **Lead Detection**: NLP-based consultation opportunity detection
- **Database**: Multi-tenant PostgreSQL with proper isolation
- **Authentication**: JWT tokens with refresh mechanism

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+ (for caching and sessions)

### Installation

```bash
# Clone repository
git clone https://github.com/techleadautopilot/platform
cd techlead-autopilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Configuration

Create `.env` file:

```env
# Application
AUTOPILOT_SECRET_KEY=your-secret-key-here
AUTOPILOT_ENVIRONMENT=development

# Database
AUTOPILOT_DATABASE_URL=postgresql://user:pass@localhost/techleadautopilot

# Redis
AUTOPILOT_REDIS_URL=redis://localhost:6379

# API Keys (optional for development)
AUTOPILOT_OPENAI_API_KEY=your-openai-key
AUTOPILOT_LINKEDIN_CLIENT_ID=your-linkedin-client-id
AUTOPILOT_LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
```

### Run Development Server

```bash
# Start API server
uvicorn techlead_autopilot.api.main:create_app --reload --host 0.0.0.0 --port 8000

# API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## API Documentation

### Content Generation

Generate technical leadership content using proven templates:

```bash
curl -X POST "http://localhost:8000/api/v1/content/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "technical_insight",
    "topic": "microservices architecture",
    "target_audience": "technical_leaders",
    "consultation_focused": true
  }'
```

### Lead Detection

Detect consultation opportunities in content:

```bash
curl -X POST "http://localhost:8000/api/v1/leads/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "We are struggling with our microservices architecture and need help with scaling our engineering team.",
    "source_platform": "linkedin",
    "author_info": {
      "title": "CTO",
      "company": "TechStartup Inc"
    }
  }'
```

## Business Model

### Subscription Tiers

- **Pro Tier**: €297/month - Individual technical leaders
- **Agency Tier**: €997/month - Consulting agencies and teams  
- **Enterprise Tier**: €2,997/month - Large organizations with custom needs

### Value Proposition

Based on proven results from €290K consultation pipeline:

- **Content Generation**: 10x faster than manual creation
- **Lead Detection**: 85%+ accuracy in identifying opportunities
- **Business Development**: Systematic pipeline generation
- **ROI**: 57:1+ LTV:CAC ratio across all tiers

## Development

### Project Structure

```
techlead-autopilot/
├── docs/                    # 12 core business documents
├── src/techlead_autopilot/  # Main application code
│   ├── api/                 # FastAPI application and routers
│   ├── core/                # Business logic (content, leads)
│   ├── services/            # External integrations
│   ├── infrastructure/      # Database, caching, etc.
│   └── config/              # Configuration management
├── tests/                   # Test suite
├── scripts/                 # Development and deployment scripts
└── deployment/              # Infrastructure as code
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=techlead_autopilot

# Run specific test categories
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black src/ tests/
ruff format src/ tests/

# Lint code
ruff check src/ tests/
mypy src/
```

## Deployment

### Production Environment

- **Platform**: AWS/GCP with Docker containers
- **Database**: Managed PostgreSQL with read replicas
- **Caching**: Redis cluster
- **CDN**: CloudFlare for static assets
- **Monitoring**: Prometheus + Grafana + Sentry

### Environment Variables

See `src/techlead_autopilot/config/settings.py` for complete configuration options.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run quality checks (`make lint test`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## License

This project is proprietary software. All rights reserved.

## Support

- Documentation: https://docs.techleadautopilot.com
- Support: support@techleadautopilot.com
- Issues: https://github.com/techleadautopilot/platform/issues

---

Built with ❤️ for technical leaders who want to scale their impact and grow their consulting business systematically.