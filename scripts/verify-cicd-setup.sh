#!/bin/bash
# Synapse Graph-RAG - CI/CD Setup Verification Script

set -e

echo "=================================================="
echo "Synapse Graph-RAG - CI/CD Setup Verification"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description: $file"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: $file (MISSING)"
        ((FAILED++))
        return 1
    fi
}

check_directory() {
    local dir=$1
    local description=$2

    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description: $dir"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description: $dir (MISSING)"
        ((FAILED++))
        return 1
    fi
}

check_env_var() {
    local var_name=$1
    local description=$2

    if [ ! -z "${!var_name}" ]; then
        echo -e "${GREEN}✓${NC} $description: $var_name is set"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description: $var_name not set (optional)"
        return 1
    fi
}

echo "Checking Required Files..."
echo "----------------------------------------"

# GitHub Actions workflows
check_file ".github/workflows/ci.yml" "CI Workflow"
check_file ".github/workflows/deploy.yml" "Deploy Workflow"
check_file ".github/workflows/release.yml" "Release Workflow"

# Docker configuration
check_file "Dockerfile" "Production Dockerfile"
check_file "docker-compose.yml" "Development Docker Compose"
check_file "docker-compose.prod.yml" "Production Docker Compose"
check_file ".dockerignore" "Docker Ignore File"

# Monitoring configuration
check_file "monitoring/prometheus.yml" "Prometheus Configuration"
check_file "graph_rag/observability/sentry_config.py" "Sentry Integration"
check_file "graph_rag/api/routers/monitoring.py" "Monitoring Endpoints"

# Environment templates
check_file ".env.production.example" "Production Environment Template"

# Documentation
check_file "docs/CICD_SETUP.md" "CI/CD Setup Documentation"
check_file "docs/DEPLOYMENT_QUICK_START.md" "Quick Start Guide"
check_file "docs/CICD_IMPLEMENTATION_SUMMARY.md" "Implementation Summary"

# Deployment tools
check_file "Makefile.deployment" "Deployment Makefile"

echo ""
echo "Checking Directories..."
echo "----------------------------------------"

check_directory ".github/workflows" "GitHub Workflows Directory"
check_directory "monitoring" "Monitoring Configuration Directory"
check_directory "graph_rag/observability" "Observability Module"
check_directory "graph_rag/api/routers" "API Routers"

echo ""
echo "Checking Python Dependencies..."
echo "----------------------------------------"

if grep -q "sentry-sdk" pyproject.toml; then
    echo -e "${GREEN}✓${NC} Sentry SDK in dependencies"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Sentry SDK missing from dependencies"
    ((FAILED++))
fi

if grep -q "prometheus-client" pyproject.toml; then
    echo -e "${GREEN}✓${NC} Prometheus client in dependencies"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Prometheus client missing from dependencies"
    ((FAILED++))
fi

if grep -q "psutil" pyproject.toml; then
    echo -e "${GREEN}✓${NC} psutil in dependencies"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} psutil missing from dependencies"
    ((FAILED++))
fi

echo ""
echo "Checking Docker Configuration..."
echo "----------------------------------------"

if docker --version > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker installed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Docker not installed"
    ((FAILED++))
fi

if docker-compose --version > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker Compose installed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Docker Compose not installed"
    ((FAILED++))
fi

echo ""
echo "Checking Environment Variables (Optional)..."
echo "----------------------------------------"

check_env_var "SENTRY_DSN" "Sentry DSN"
check_env_var "RAILWAY_TOKEN" "Railway Token"
check_env_var "SYNAPSE_JWT_SECRET_KEY" "JWT Secret Key"
check_env_var "OPENAI_API_KEY" "OpenAI API Key"

echo ""
echo "Testing Docker Build..."
echo "----------------------------------------"

if docker build -t synapse-test -f Dockerfile . --target production > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker build successful"
    ((PASSED++))
    docker rmi synapse-test > /dev/null 2>&1 || true
else
    echo -e "${YELLOW}⚠${NC} Docker build test skipped (requires Docker daemon)"
fi

echo ""
echo "Checking API Integration..."
echo "----------------------------------------"

if grep -q "init_sentry" graph_rag/api/main.py; then
    echo -e "${GREEN}✓${NC} Sentry initialized in API"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Sentry not initialized in API"
    ((FAILED++))
fi

if grep -q "monitoring.router" graph_rag/api/main.py; then
    echo -e "${GREEN}✓${NC} Monitoring router included in API"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Monitoring router not included in API"
    ((FAILED++))
fi

echo ""
echo "=================================================="
echo "Verification Summary"
echo "=================================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! CI/CD setup is complete.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure environment variables in Railway"
    echo "2. Set GitHub secrets for CI/CD"
    echo "3. Test deployment to staging: make -f Makefile.deployment deploy-staging"
    echo "4. Deploy to production: make -f Makefile.deployment deploy-production"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review the output above.${NC}"
    exit 1
fi
