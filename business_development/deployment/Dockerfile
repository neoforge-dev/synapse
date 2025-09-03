# Production LinkedIn Automation Docker Container
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    cron \
    supervisor \
    nginx \
    certbot \
    python3-certbot-nginx \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd --create-home --shell /bin/bash linkedin_automation

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY business_development/ ./business_development/
COPY analytics/ ./analytics/
COPY *.py ./

# Create necessary directories
RUN mkdir -p /var/log/linkedin_automation \
    && mkdir -p /app/data \
    && mkdir -p /app/backups \
    && mkdir -p /app/ssl

# Set proper permissions
RUN chown -R linkedin_automation:linkedin_automation /app \
    && chown -R linkedin_automation:linkedin_automation /var/log/linkedin_automation

# Copy configuration files
COPY deployment/supervisord.conf /etc/supervisor/conf.d/
COPY deployment/nginx.conf /etc/nginx/sites-available/linkedin-automation
COPY deployment/crontab /etc/cron.d/linkedin-automation

# Enable nginx site
RUN ln -s /etc/nginx/sites-available/linkedin-automation /etc/nginx/sites-enabled/ \
    && rm /etc/nginx/sites-enabled/default

# Set cron permissions
RUN chmod 0644 /etc/cron.d/linkedin-automation \
    && crontab /etc/cron.d/linkedin-automation

# Expose ports
EXPOSE 80 443 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to application user for security
USER linkedin_automation

# Start supervisor to manage all services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]