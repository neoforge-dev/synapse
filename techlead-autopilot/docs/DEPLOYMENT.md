# Production Deployment Guide

**TechLead AutoPilot** production deployment guide for enterprise-grade SaaS infrastructure with high availability, security, and scalability.

## 🏗️ **Architecture Overview**

The platform is designed as a **cloud-native, multi-tenant SaaS** with the following components:

- **FastAPI Backend** - Async web framework with auto-scaling
- **PostgreSQL Database** - Primary data store with read replicas
- **Redis Cluster** - Session storage, caching, and rate limiting
- **Next.js Frontend** - TypeScript web application with PWA features
- **CDN** - Static asset delivery and DDoS protection
- **Load Balancer** - Traffic distribution and SSL termination
- **Container Registry** - Docker image storage and deployment
- **Monitoring Stack** - Logging, metrics, and alerting

## ☁️ **Cloud Provider Setup**

### AWS Deployment

#### **Core Services**
- **ECS/Fargate** - Container orchestration with auto-scaling
- **RDS PostgreSQL** - Managed database with Multi-AZ
- **ElastiCache Redis** - Managed Redis cluster
- **Application Load Balancer** - Layer 7 load balancing
- **CloudFront** - CDN and DDoS protection
- **Route 53** - DNS management
- **S3** - File storage and static assets
- **ECR** - Container registry
- **Secrets Manager** - Secure credential storage

#### **Infrastructure as Code (Terraform)**
```hcl
# terraform/main.tf
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "techlead-autopilot"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
}

module "rds" {
  source = "terraform-aws-modules/rds/aws"
  
  identifier = "techlead-autopilot-prod"
  
  engine            = "postgres"
  engine_version    = "14.9"
  instance_class    = "db.r6g.xlarge"
  allocated_storage = 100
  storage_encrypted = true
  
  db_name  = "techleadautopilot"
  username = "postgres"
  manage_master_user_password = true
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  backup_window      = "03:00-04:00"
  backup_retention_period = 30
  
  create_db_subnet_group = true
  subnet_ids = module.vpc.private_subnets
  
  multi_az = true
  
  tags = local.tags
}

module "elasticache" {
  source = "terraform-aws-modules/elasticache/aws"
  
  cluster_id         = "techlead-autopilot"
  node_type         = "cache.r6g.large"
  num_cache_nodes   = 3
  parameter_group_name = "default.redis7"
  
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  tags = local.tags
}
```

### Google Cloud Platform (GCP) Deployment

#### **Core Services**
- **Cloud Run** - Serverless container platform
- **Cloud SQL** - Managed PostgreSQL with HA
- **Memorystore** - Managed Redis
- **Cloud Load Balancing** - Global load balancer
- **Cloud CDN** - Content delivery network
- **Cloud DNS** - DNS management
- **Cloud Storage** - File storage
- **Artifact Registry** - Container registry
- **Secret Manager** - Secure credential storage

#### **Infrastructure as Code (Terraform)**
```hcl
# terraform/gcp.tf
resource "google_cloud_run_service" "api" {
  name     = "techlead-autopilot-api"
  location = var.region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/techlead-autopilot:latest"
        
        ports {
          container_port = 8000
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.app.name}:${google_sql_user.app.password}@${google_sql_database_instance.main.private_ip_address}/techleadautopilot"
        }
        
        env {
          name  = "REDIS_URL"  
          value = "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}"
        }
        
        resources {
          limits = {
            cpu    = "2000m"
            memory = "4Gi"
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "2"
        "autoscaling.knative.dev/maxScale" = "100"
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }
}

resource "google_sql_database_instance" "main" {
  name             = "techlead-autopilot-prod"
  database_version = "POSTGRES_14"
  region           = var.region
  
  settings {
    tier = "db-custom-4-16384"  # 4 vCPUs, 16GB RAM
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 30
      }
    }
    
    availability_type = "REGIONAL"  # High availability
    
    disk_type = "PD_SSD"
    disk_size = 100
    disk_autoresize = true
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }
  }
  
  depends_on = [google_service_networking_connection.private_vpc_connection]
}
```

## 🐳 **Container Configuration**

### Multi-Stage Dockerfile

```dockerfile
# Dockerfile
# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Stage 2: Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini ./

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "techlead_autopilot.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/techleadautopilot
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: techleadautopilot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## 🔧 **Configuration Management**

### Production Environment Variables

```bash
# .env.production
# Application Core
TECHLEAD_AUTOPILOT_ENVIRONMENT=production
TECHLEAD_AUTOPILOT_SECRET_KEY=your-256-bit-secret-key-here
TECHLEAD_AUTOPILOT_DEBUG=false

# Database
TECHLEAD_AUTOPILOT_DATABASE_URL=postgresql://username:password@db-host:5432/techleadautopilot
TECHLEAD_AUTOPILOT_DATABASE_POOL_SIZE=20
TECHLEAD_AUTOPILOT_DATABASE_ECHO=false

# Redis
TECHLEAD_AUTOPILOT_REDIS_URL=redis://redis-cluster-endpoint:6379/0
TECHLEAD_AUTOPILOT_REDIS_KEY_PREFIX=autopilot:prod:

# Security
TECHLEAD_AUTOPILOT_ACCESS_TOKEN_EXPIRE_MINUTES=30
TECHLEAD_AUTOPILOT_REFRESH_TOKEN_EXPIRE_DAYS=7
TECHLEAD_AUTOPILOT_ENABLE_RATE_LIMITING=true
TECHLEAD_AUTOPILOT_ENABLE_SECURITY_MIDDLEWARE=true

# External APIs
TECHLEAD_AUTOPILOT_OPENAI_API_KEY=your-openai-key
TECHLEAD_AUTOPILOT_LINKEDIN_CLIENT_ID=your-linkedin-client-id
TECHLEAD_AUTOPILOT_LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
TECHLEAD_AUTOPILOT_STRIPE_SECRET_KEY=your-stripe-secret-key
TECHLEAD_AUTOPILOT_STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Monitoring
TECHLEAD_AUTOPILOT_SENTRY_DSN=your-sentry-dsn
TECHLEAD_AUTOPILOT_LOG_LEVEL=INFO
TECHLEAD_AUTOPILOT_STRUCTURED_LOGGING=true
TECHLEAD_AUTOPILOT_LOG_FORMAT=json

# Performance
TECHLEAD_AUTOPILOT_PROMETHEUS_ENABLED=true
TECHLEAD_AUTOPILOT_HEALTH_CHECK_INTERVAL=30
```

### Kubernetes Configuration

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techlead-autopilot-api
  labels:
    app: techlead-autopilot
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: techlead-autopilot
      component: api
  template:
    metadata:
      labels:
        app: techlead-autopilot
        component: api
    spec:
      containers:
      - name: api
        image: your-registry/techlead-autopilot:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: techlead-autopilot-api-service
spec:
  selector:
    app: techlead-autopilot
    component: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

## 📊 **Monitoring & Observability**

### Health Checks

```python
# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/ready")
async def readiness_check():
    """Readiness check with dependency validation."""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "external_apis": await check_external_apis()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        content={"status": "ready" if all_healthy else "not_ready", "checks": checks},
        status_code=status_code
    )
```

### Prometheus Metrics

```python
# Metrics collection
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    
    return response
```

### Logging Configuration

```python
# Structured logging for production
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/app/application.log",
            "maxBytes": 52428800,  # 50MB
            "backupCount": 10,
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

## 🔄 **CI/CD Pipeline**

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install uv
      run: pip install uv
    
    - name: Install dependencies
      run: uv sync --dev
    
    - name: Run tests
      run: |
        uv run pytest --cov=techlead_autopilot --cov-report=xml
        uv run ruff check .
        uv run mypy src/techlead_autopilot
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run security scan
      run: |
        uv run bandit -r src/
        uv run safety check

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        # Deploy using your preferred method (ECS, Cloud Run, Kubernetes, etc.)
        echo "Deploying to production..."
```

## 🚀 **Deployment Steps**

### 1. Infrastructure Setup

```bash
# 1. Create infrastructure with Terraform
cd terraform/
terraform init
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"

# 2. Configure DNS
# Point your domain to the load balancer IP/CNAME

# 3. Set up SSL certificates
# Use AWS Certificate Manager or Let's Encrypt
```

### 2. Database Setup

```bash
# 1. Create database and user
psql -h your-db-host -U postgres -c "CREATE DATABASE techleadautopilot;"
psql -h your-db-host -U postgres -c "CREATE USER autopilot_user WITH PASSWORD 'secure_password';"
psql -h your-db-host -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE techleadautopilot TO autopilot_user;"

# 2. Run migrations
uv run alembic upgrade head

# 3. Create initial data (optional)
uv run python scripts/seed_data.py
```

### 3. Application Deployment

```bash
# 1. Build and push Docker image
docker build -t your-registry/techlead-autopilot:latest .
docker push your-registry/techlead-autopilot:latest

# 2. Deploy to container orchestrator
# For ECS:
aws ecs update-service --cluster production --service techlead-autopilot --force-new-deployment

# For Kubernetes:
kubectl apply -f k8s/
kubectl rollout restart deployment/techlead-autopilot-api

# For Cloud Run:
gcloud run deploy techlead-autopilot-api \
  --image gcr.io/your-project/techlead-autopilot:latest \
  --region us-central1 \
  --platform managed
```

### 4. Post-Deployment Verification

```bash
# 1. Health checks
curl https://your-domain.com/health
curl https://your-domain.com/ready

# 2. API functionality
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# 3. Monitor logs
kubectl logs deployment/techlead-autopilot-api

# 4. Check metrics
curl https://your-domain.com/metrics
```

## 📈 **Scaling & Performance**

### Horizontal Scaling

```yaml
# Auto-scaling configuration for Kubernetes
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: techlead-autopilot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: techlead-autopilot-api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling

```python
# Read replica configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'techleadautopilot',
        'USER': 'autopilot_user',
        'PASSWORD': 'password',
        'HOST': 'primary-db-host',
        'PORT': '5432',
    },
    'read_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'techleadautopilot',
        'USER': 'autopilot_user',  
        'PASSWORD': 'password',
        'HOST': 'read-replica-host',
        'PORT': '5432',
    }
}
```

### Redis Clustering

```python
# Redis cluster configuration
import redis.sentinel

sentinels = [
    ('sentinel1.example.com', 26379),
    ('sentinel2.example.com', 26379),
    ('sentinel3.example.com', 26379)
]

sentinel = redis.sentinel.Sentinel(sentinels, socket_timeout=0.1)
redis_client = sentinel.master_for('mymaster', socket_timeout=0.1)
```

## 🛡️ **Security Hardening**

### Network Security

```bash
# Security group rules (AWS)
# Allow HTTPS traffic
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Allow application traffic only from load balancer
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxx \
  --protocol tcp \
  --port 8000 \
  --source-group sg-yyyyyy
```

### SSL/TLS Configuration

```nginx
# nginx configuration for SSL
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/your-domain.com.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.com.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📋 **Deployment Checklist**

### Pre-Deployment

#### **Infrastructure**
- [ ] Cloud resources provisioned and configured
- [ ] DNS records configured and propagated
- [ ] SSL certificates valid and installed
- [ ] Load balancer configured with health checks
- [ ] Database setup with proper backups configured
- [ ] Redis cluster configured and tested
- [ ] Monitoring and logging infrastructure ready

#### **Security**
- [ ] Secrets properly stored in secret management system
- [ ] Network security groups/firewall rules configured
- [ ] Security scanning completed (no critical vulnerabilities)
- [ ] Rate limiting and DDoS protection configured
- [ ] Security headers properly configured

#### **Application**
- [ ] Environment variables configured for production
- [ ] Database migrations tested and ready to run
- [ ] Application health checks configured
- [ ] Error tracking (Sentry) configured
- [ ] Performance monitoring configured

### Post-Deployment

#### **Verification**
- [ ] All health checks passing
- [ ] API endpoints responding correctly
- [ ] Database connectivity confirmed
- [ ] Redis connectivity confirmed  
- [ ] External API integrations working (LinkedIn, OpenAI, Stripe)
- [ ] SSL certificate valid and properly configured
- [ ] Security headers present in responses

#### **Monitoring**
- [ ] Application logs flowing to centralized logging
- [ ] Metrics being collected and dashboards working
- [ ] Alerting rules configured and tested
- [ ] Error tracking receiving errors correctly
- [ ] Performance monitoring showing expected metrics

#### **Business Continuity**
- [ ] Backup and recovery procedures tested
- [ ] Disaster recovery plan documented and tested
- [ ] Scaling thresholds configured and tested
- [ ] Incident response procedures documented
- [ ] Team trained on production operations

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Owner**: DevOps Team  
**Review Cycle**: Monthly