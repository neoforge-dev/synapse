#!/bin/bash
# Production Deployment Script for LinkedIn Automation
# Usage: ./deploy.sh [environment] [action]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENVIRONMENT="${1:-production}"
ACTION="${2:-deploy}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validation functions
validate_environment() {
    log_info "Validating environment configuration..."
    
    # Check required environment variables
    required_vars=(
        "LINKEDIN_API_TOKEN"
        "NOTIFICATION_EMAIL"
        "SMTP_USERNAME"
        "SMTP_PASSWORD"
        "JWT_SECRET_KEY"
        "API_SECRET_KEY"
        "DOMAIN_NAME"
        "SSL_EMAIL"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
    fi
    
    log_success "Environment validation passed"
}

validate_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is required but not installed"
    fi
    
    # Check system resources
    available_memory=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $available_memory -lt 2048 ]]; then
        log_warning "System has less than 2GB RAM. Performance may be affected."
    fi
    
    # Check disk space
    available_disk=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_disk -lt 5242880 ]]; then  # 5GB in KB
        log_warning "Less than 5GB disk space available"
    fi
    
    log_success "Prerequisites validation passed"
}

# Setup functions
setup_directories() {
    log_info "Setting up production directories..."
    
    # Create production directories
    sudo mkdir -p /opt/linkedin_automation/{data,backups,logs,ssl,config}
    sudo chown -R 1000:1000 /opt/linkedin_automation
    
    # Set proper permissions
    chmod 755 /opt/linkedin_automation
    chmod 750 /opt/linkedin_automation/{data,backups}
    chmod 755 /opt/linkedin_automation/logs
    
    log_success "Production directories created"
}

setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    if [[ "${ENABLE_SSL:-true}" == "true" ]]; then
        # Install certbot if not present
        if ! command -v certbot &> /dev/null; then
            log_info "Installing certbot..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y certbot python3-certbot-nginx
            elif command -v yum &> /dev/null; then
                sudo yum install -y certbot python3-certbot-nginx
            else
                log_warning "Please install certbot manually"
            fi
        fi
        
        # Generate SSL certificate
        if [[ ! -f "/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem" ]]; then
            log_info "Generating SSL certificate for ${DOMAIN_NAME}..."
            sudo certbot certonly --standalone --non-interactive --agree-tos \
                --email "${SSL_EMAIL}" -d "${DOMAIN_NAME}" -d "www.${DOMAIN_NAME}"
        fi
    fi
    
    log_success "SSL setup completed"
}

setup_monitoring() {
    log_info "Setting up monitoring configuration..."
    
    # Create Grafana provisioning directories
    mkdir -p "${SCRIPT_DIR}/monitoring/grafana/"{dashboards,datasources}
    
    # Create Grafana datasource configuration
    cat > "${SCRIPT_DIR}/monitoring/grafana/datasources/prometheus.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    
    # Create dashboard configuration
    cat > "${SCRIPT_DIR}/monitoring/grafana/dashboards/dashboards.yml" << EOF
apiVersion: 1

providers:
  - name: 'LinkedIn Automation'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
    
    log_success "Monitoring configuration created"
}

# Deployment functions
deploy_application() {
    log_info "Deploying LinkedIn automation application..."
    
    cd "$SCRIPT_DIR"
    
    # Build and start services
    docker-compose -f docker-compose.yml build --no-cache
    docker-compose -f docker-compose.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    max_attempts=30
    attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            log_success "Application is healthy and ready"
            break
        fi
        
        attempt=$((attempt + 1))
        log_info "Health check attempt $attempt/$max_attempts..."
        sleep 10
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Application failed to become healthy within timeout"
    fi
}

setup_firewall() {
    log_info "Configuring firewall rules..."
    
    # Configure UFW (Ubuntu Firewall) if available
    if command -v ufw &> /dev/null; then
        sudo ufw --force reset
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        
        # Allow SSH
        sudo ufw allow ssh
        
        # Allow HTTP/HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        # Allow monitoring (restrict to specific IPs in production)
        sudo ufw allow from 10.0.0.0/8 to any port 3000
        sudo ufw allow from 172.16.0.0/12 to any port 3000
        sudo ufw allow from 192.168.0.0/16 to any port 3000
        
        sudo ufw --force enable
        log_success "Firewall configured"
    else
        log_warning "UFW not available, configure firewall manually"
    fi
}

setup_systemd_service() {
    log_info "Creating systemd service for LinkedIn automation..."
    
    cat > /tmp/linkedin-automation.service << EOF
[Unit]
Description=LinkedIn Automation Production Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/linkedin-automation.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable linkedin-automation.service
    
    log_success "Systemd service created and enabled"
}

# Backup and maintenance functions
create_backup() {
    log_info "Creating system backup..."
    
    backup_dir="/opt/linkedin_automation/backups/pre_deployment_${TIMESTAMP}"
    mkdir -p "$backup_dir"
    
    # Backup databases
    if [[ -d "/opt/linkedin_automation/data" ]]; then
        cp -r /opt/linkedin_automation/data "$backup_dir/"
    fi
    
    # Backup configuration
    if [[ -d "/opt/linkedin_automation/config" ]]; then
        cp -r /opt/linkedin_automation/config "$backup_dir/"
    fi
    
    # Create archive
    tar -czf "/opt/linkedin_automation/backups/backup_${TIMESTAMP}.tar.gz" -C "$backup_dir" .
    rm -rf "$backup_dir"
    
    log_success "Backup created: backup_${TIMESTAMP}.tar.gz"
}

# Main deployment workflow
main() {
    case "$ACTION" in
        "validate")
            validate_environment
            validate_prerequisites
            ;;
        "setup")
            validate_environment
            validate_prerequisites
            setup_directories
            setup_ssl
            setup_monitoring
            setup_firewall
            ;;
        "deploy")
            log_info "Starting full deployment for environment: $ENVIRONMENT"
            
            # Pre-deployment steps
            validate_environment
            validate_prerequisites
            create_backup
            setup_directories
            setup_ssl
            setup_monitoring
            
            # Deploy application
            deploy_application
            
            # Post-deployment setup
            setup_systemd_service
            setup_firewall
            
            # Final verification
            log_info "Running post-deployment verification..."
            sleep 10
            
            if curl -f http://localhost:8000/health &>/dev/null; then
                log_success "🚀 LinkedIn Automation deployed successfully!"
                log_info "Dashboard: https://${DOMAIN_NAME}"
                log_info "API Health: https://${DOMAIN_NAME}/health"
                log_info "Monitoring: https://${DOMAIN_NAME}/monitoring"
            else
                log_error "Deployment verification failed"
            fi
            ;;
        "update")
            log_info "Updating LinkedIn automation application..."
            create_backup
            cd "$SCRIPT_DIR"
            docker-compose pull
            docker-compose up -d
            log_success "Application updated successfully"
            ;;
        "rollback")
            log_info "Rolling back to previous version..."
            # Implementation for rollback would go here
            log_warning "Rollback functionality not implemented yet"
            ;;
        "status")
            log_info "Checking application status..."
            cd "$SCRIPT_DIR"
            docker-compose ps
            ;;
        "logs")
            log_info "Showing application logs..."
            cd "$SCRIPT_DIR"
            docker-compose logs -f --tail=100
            ;;
        "stop")
            log_info "Stopping LinkedIn automation..."
            cd "$SCRIPT_DIR"
            docker-compose down
            log_success "Application stopped"
            ;;
        *)
            echo "Usage: $0 [environment] [action]"
            echo "Environments: production, staging"
            echo "Actions: validate, setup, deploy, update, rollback, status, logs, stop"
            exit 1
            ;;
    esac
}

# Error handling
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"