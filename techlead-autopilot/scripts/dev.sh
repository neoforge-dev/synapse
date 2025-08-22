#!/bin/bash

# TechLead AutoPilot Development Scripts
# Usage: ./scripts/dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        error "uv is not installed. Please install it first: pip install uv"
    fi
}

# Check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker first."
    fi
}

# Setup development environment
setup() {
    info "Setting up TechLead AutoPilot development environment..."
    
    check_uv
    
    # Create virtual environment
    info "Creating virtual environment..."
    uv venv
    
    # Install dependencies
    info "Installing dependencies..."
    source .venv/bin/activate
    uv pip install -e ".[dev]"
    
    # Copy environment template
    if [ ! -f .env ]; then
        info "Creating .env file from template..."
        cat > .env << EOF
# TechLead AutoPilot Development Environment

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
TECHLEAD_JWT_SECRET_KEY=dev-secret-key-change-in-production
TECHLEAD_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
TECHLEAD_JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# External APIs (add your keys here)
TECHLEAD_LINKEDIN_CLIENT_ID=
TECHLEAD_LINKEDIN_CLIENT_SECRET=
TECHLEAD_OPENAI_API_KEY=
TECHLEAD_STRIPE_SECRET_KEY=
TECHLEAD_STRIPE_WEBHOOK_SECRET=

# Features
TECHLEAD_ENABLE_RATE_LIMITING=true
TECHLEAD_ENABLE_ANALYTICS=true
TECHLEAD_ENABLE_CACHING=true
EOF
        warning "Please update .env file with your API keys and configuration"
    fi
    
    success "Development environment setup complete!"
    info "Next steps:"
    info "  1. Update .env file with your API keys"
    info "  2. Run: ./scripts/dev.sh start-services"
    info "  3. Run: ./scripts/dev.sh migrate"
    info "  4. Run: ./scripts/dev.sh dev"
}

# Start development services
start_services() {
    info "Starting development services..."
    check_docker
    
    # Start PostgreSQL and Redis
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    info "Waiting for services to be ready..."
    timeout 30 bash -c '
        until docker-compose exec postgres pg_isready -U postgres; do 
            echo "Waiting for PostgreSQL..."
            sleep 1
        done
    '
    
    timeout 30 bash -c '
        until docker-compose exec redis redis-cli ping | grep PONG; do 
            echo "Waiting for Redis..."
            sleep 1
        done
    '
    
    success "Services are ready!"
}

# Stop development services
stop_services() {
    info "Stopping development services..."
    docker-compose down
    success "Services stopped!"
}

# Run database migrations
migrate() {
    info "Running database migrations..."
    
    source .venv/bin/activate
    uv run alembic upgrade head
    
    success "Database migrations complete!"
}

# Create new migration
create_migration() {
    if [ -z "$2" ]; then
        error "Please provide a migration message: ./scripts/dev.sh create-migration 'your message'"
    fi
    
    info "Creating new migration: $2"
    
    source .venv/bin/activate
    uv run alembic revision --autogenerate -m "$2"
    
    success "Migration created!"
}

# Run development server
dev() {
    info "Starting development server..."
    
    source .venv/bin/activate
    uv run uvicorn techlead_autopilot.api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
}

# Run tests
test() {
    info "Running tests..."
    
    source .venv/bin/activate
    
    # Run different test types based on argument
    case "${2:-all}" in
        "unit")
            uv run pytest tests/unit/ -v
            ;;
        "integration")
            uv run pytest tests/integration/ -v
            ;;
        "coverage")
            uv run pytest --cov=techlead_autopilot --cov-report=html --cov-report=term -v
            ;;
        *)
            uv run pytest -v
            ;;
    esac
    
    success "Tests completed!"
}

# Lint and format code
lint() {
    info "Running code quality checks..."
    
    source .venv/bin/activate
    
    # Ruff linting
    info "Running ruff linter..."
    uv run ruff check .
    
    # Ruff formatting
    info "Running ruff formatter..."
    uv run ruff format .
    
    # MyPy type checking
    info "Running mypy type checker..."
    uv run mypy src/techlead_autopilot --ignore-missing-imports || warning "Type checking completed with warnings"
    
    success "Code quality checks completed!"
}

# Security scan
security() {
    info "Running security scans..."
    
    source .venv/bin/activate
    
    # Install security tools if not present
    uv pip install bandit safety
    
    # Bandit security scan
    info "Running bandit security scanner..."
    uv run bandit -r src/techlead_autopilot -f json -o bandit-report.json
    uv run bandit -r src/techlead_autopilot || warning "Bandit found potential security issues"
    
    # Safety vulnerability scan
    info "Running safety vulnerability scanner..."
    uv run safety check || warning "Safety found potential vulnerabilities"
    
    success "Security scans completed!"
}

# Build Docker image
build() {
    info "Building Docker image..."
    
    check_docker
    docker build -t techlead-autopilot:dev .
    
    success "Docker image built successfully!"
}

# Reset development environment
reset() {
    warning "This will destroy all local data. Are you sure? (y/N)"
    read -r confirmation
    
    if [[ ! "$confirmation" =~ ^[Yy]$ ]]; then
        info "Reset cancelled."
        exit 0
    fi
    
    info "Resetting development environment..."
    
    # Stop and remove containers
    docker-compose down -v
    
    # Remove virtual environment
    rm -rf .venv
    
    # Recreate environment
    setup
    start_services
    migrate
    
    success "Development environment reset complete!"
}

# Show help
help() {
    echo "TechLead AutoPilot Development Scripts"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup           - Set up development environment"
    echo "  start-services  - Start PostgreSQL and Redis services"
    echo "  stop-services   - Stop development services"
    echo "  migrate         - Run database migrations"
    echo "  create-migration 'message' - Create new migration"
    echo "  dev             - Start development server with hot reload"
    echo "  test [type]     - Run tests (unit|integration|coverage|all)"
    echo "  lint            - Run code quality checks (ruff, mypy)"
    echo "  security        - Run security scans (bandit, safety)"
    echo "  build           - Build Docker image"
    echo "  reset           - Reset entire development environment"
    echo "  help            - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/dev.sh setup"
    echo "  ./scripts/dev.sh test unit"
    echo "  ./scripts/dev.sh create-migration 'add user preferences table'"
}

# Main script logic
case "${1:-help}" in
    "setup")
        setup
        ;;
    "start-services")
        start_services
        ;;
    "stop-services")
        stop_services
        ;;
    "migrate")
        migrate
        ;;
    "create-migration")
        create_migration "$@"
        ;;
    "dev")
        dev
        ;;
    "test")
        test "$@"
        ;;
    "lint")
        lint
        ;;
    "security")
        security
        ;;
    "build")
        build
        ;;
    "reset")
        reset
        ;;
    "help")
        help
        ;;
    *)
        error "Unknown command: $1. Run './scripts/dev.sh help' for available commands."
        ;;
esac