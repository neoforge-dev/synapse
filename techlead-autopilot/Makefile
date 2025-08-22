# TechLead AutoPilot - Development Makefile

.PHONY: help setup dev test lint security build clean install docs

# Default target
help: ## Show this help message
	@echo "TechLead AutoPilot - Development Commands"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Set up development environment
	./scripts/dev.sh setup

install: ## Install dependencies only
	uv pip install -e ".[dev]"

# Development
dev: ## Start development server
	./scripts/dev.sh dev

start-services: ## Start PostgreSQL and Redis services
	./scripts/dev.sh start-services

stop-services: ## Stop development services
	./scripts/dev.sh stop-services

migrate: ## Run database migrations
	./scripts/dev.sh migrate

migration: ## Create new migration (usage: make migration msg="your message")
	./scripts/dev.sh create-migration "$(msg)"

# Testing
test: ## Run all tests
	./scripts/dev.sh test

test-unit: ## Run unit tests only
	./scripts/dev.sh test unit

test-integration: ## Run integration tests only
	./scripts/dev.sh test integration

test-coverage: ## Run tests with coverage report
	./scripts/dev.sh test coverage

# Code Quality
lint: ## Run linting and formatting
	./scripts/dev.sh lint

format: ## Format code with ruff
	uv run ruff format .

check: ## Check code without formatting
	uv run ruff check .
	uv run mypy src/techlead_autopilot --ignore-missing-imports

# Security
security: ## Run security scans
	./scripts/dev.sh security

audit: ## Audit dependencies for vulnerabilities
	uv run safety check

# Building and Deployment
build: ## Build Docker image
	./scripts/dev.sh build

build-prod: ## Build production Docker image
	docker build --target production -t techlead-autopilot:latest .

# Database operations
db-reset: ## Reset database (WARNING: destroys all data)
	docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS techlead_autopilot;"
	docker-compose exec postgres psql -U postgres -c "CREATE DATABASE techlead_autopilot;"
	./scripts/dev.sh migrate

db-shell: ## Open database shell
	docker-compose exec postgres psql -U postgres -d techlead_autopilot

# Docker operations
up: ## Start all services with Docker Compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show service logs
	docker-compose logs -f

# Maintenance
clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/
	rm -f bandit-report.json safety-report.json

reset: ## Reset entire development environment
	./scripts/dev.sh reset

# Documentation
docs: ## Generate API documentation
	@echo "API Documentation available at: http://localhost:8000/docs"
	@echo "Start the development server with 'make dev' to view documentation"

api-docs: ## Open API documentation in browser
	python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')"

# Shortcuts for common workflows
quick-start: setup start-services migrate ## Quick start: setup, start services, and run migrations
	@echo "✅ Quick start complete! Run 'make dev' to start the development server"

ci: lint security test-coverage ## Run all CI checks locally
	@echo "✅ All CI checks passed!"

deploy-check: lint security test build ## Pre-deployment checks
	@echo "✅ Ready for deployment!"

# Development workflow helpers
fix: format lint ## Fix formatting and linting issues
	@echo "✅ Code formatting and linting fixes applied!"

check-all: lint security test-coverage ## Run all quality checks
	@echo "✅ All quality checks completed!"

# Environment management
env-example: ## Create .env.example file
	@cat > .env.example << 'EOF'
	# TechLead AutoPilot Configuration Template
	# Copy this file to .env and update with your values
	
	# Database
	TECHLEAD_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/techlead_autopilot
	
	# Redis
	TECHLEAD_REDIS_URL=redis://localhost:6379/0
	
	# API Configuration  
	TECHLEAD_ENVIRONMENT=development
	TECHLEAD_API_HOST=0.0.0.0
	TECHLEAD_API_PORT=8000
	TECHLEAD_DEBUG=true
	TECHLEAD_LOG_LEVEL=DEBUG
	
	# Security
	TECHLEAD_JWT_SECRET_KEY=your-secret-key-here
	TECHLEAD_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
	TECHLEAD_JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
	
	# External APIs
	TECHLEAD_LINKEDIN_CLIENT_ID=your-linkedin-client-id
	TECHLEAD_LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
	TECHLEAD_OPENAI_API_KEY=your-openai-api-key
	TECHLEAD_STRIPE_SECRET_KEY=your-stripe-secret-key
	TECHLEAD_STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
	
	# Features
	TECHLEAD_ENABLE_RATE_LIMITING=true
	TECHLEAD_ENABLE_ANALYTICS=true
	TECHLEAD_ENABLE_CACHING=true
	EOF
	@echo "✅ .env.example created!"