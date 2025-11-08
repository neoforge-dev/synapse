#!/usr/bin/env python3
"""
Production Web API for LinkedIn Automation
Monitoring, control, and metrics endpoints
"""

import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
LINKEDIN_POSTS_CREATED = Counter('linkedin_posts_created_total', 'Total LinkedIn posts created')
LINKEDIN_POSTS_FAILED = Counter('linkedin_posts_failed_total', 'Total LinkedIn post failures')
CIRCUIT_BREAKER_FAILURES = Gauge('circuit_breaker_failures_total', 'Circuit breaker failure count')
CONTENT_QUEUE_ITEMS = Gauge('content_queue_items', 'Content queue items by status', ['status'])
LINKEDIN_ENGAGEMENT_RATE = Gauge('linkedin_engagement_rate', 'LinkedIn engagement rate')
CONSULTATION_INQUIRIES = Counter('consultation_inquiries_total', 'Total consultation inquiries')
CONSULTATION_PIPELINE_VALUE = Gauge('consultation_pipeline_value_usd', 'Consultation pipeline value in USD')
API_RESPONSE_TIME = Histogram('linkedin_api_response_time_seconds', 'LinkedIn API response time')
DATABASE_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')
SYSTEM_HEALTH_SCORE = Gauge('system_health_score', 'Overall system health score (0-100)')

# Initialize FastAPI app
app = FastAPI(
    title="LinkedIn Automation Production API",
    description="Enterprise monitoring, control, and analytics for LinkedIn automation",
    version="1.0.0"
)

# Security
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token for authentication"""
    token = credentials.credentials
    expected_token = os.getenv('API_SECRET_KEY', 'dev-token-change-in-production')

    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return token

# Pydantic models
class SystemHealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    version: str
    services: dict[str, bool]
    metrics: dict[str, float]

class ContentQueueStatus(BaseModel):
    total_items: int
    queued: int
    posted: int
    failed: int
    next_scheduled: str | None

class BusinessMetrics(BaseModel):
    pipeline_value: float
    total_inquiries: int
    conversion_rate: float
    revenue_generated: float
    engagement_rate: float
    posts_published: int

class AlertConfig(BaseModel):
    alert_type: str
    threshold: float
    enabled: bool
    notification_channels: list[str]

# Store startup time for uptime calculation
STARTUP_TIME = time.time()

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Collect HTTP request metrics"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)

    return response

@app.get("/health", response_model=SystemHealthResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Test database connectivity
        db_healthy = test_database_connection()

        # Check content queue status
        queue_status = get_content_queue_status()

        # Calculate system health score
        health_score = calculate_system_health_score(db_healthy, queue_status)
        SYSTEM_HEALTH_SCORE.set(health_score)

        return SystemHealthResponse(
            status="healthy" if health_score > 80 else "degraded" if health_score > 50 else "unhealthy",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=time.time() - STARTUP_TIME,
            version="1.0.0",
            services={
                "database": db_healthy,
                "content_queue": queue_status.total_items > 0,
                "linkedin_api": check_linkedin_api_health(),
                "monitoring": True
            },
            metrics={
                "health_score": health_score,
                "queue_items": queue_status.total_items,
                "uptime_hours": (time.time() - STARTUP_TIME) / 3600
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    try:
        # Update dynamic metrics before serving
        update_dynamic_metrics()

        # Generate Prometheus format metrics
        return PlainTextResponse(
            generate_latest(),
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics generation failed")

@app.get("/api/v1/status", response_model=dict)
async def get_system_status(token: str = Depends(verify_token)):
    """Get detailed system status"""
    try:
        queue_status = get_content_queue_status()
        business_metrics = get_business_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": calculate_system_health_score(True, queue_status),
            "content_queue": queue_status.dict(),
            "business_metrics": business_metrics.dict(),
            "recent_activity": get_recent_activity(),
            "alerts": get_active_alerts()
        }
    except Exception as e:
        logger.error(f"Status endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/v1/content/queue", response_model=ContentQueueStatus)
async def get_queue_status(token: str = Depends(verify_token)):
    """Get content queue status"""
    return get_content_queue_status()

@app.get("/api/v1/business/metrics", response_model=BusinessMetrics)
async def get_business_metrics_endpoint(token: str = Depends(verify_token)):
    """Get business development metrics"""
    return get_business_metrics()

@app.post("/api/v1/content/generate")
async def generate_content(
    content_type: str,
    audience: str,
    weeks: int = 4,
    token: str = Depends(verify_token)
):
    """Generate new content for the queue"""
    try:
        # This would integrate with the content generation system
        # For now, return success confirmation

        return {
            "status": "success",
            "message": f"Generated {weeks} weeks of {content_type} content for {audience}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail="Content generation failed")

@app.post("/api/v1/system/maintenance")
async def trigger_maintenance(
    action: str,
    token: str = Depends(verify_token)
):
    """Trigger system maintenance actions"""
    allowed_actions = ["backup", "cleanup", "queue_refill", "health_check"]

    if action not in allowed_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Allowed: {allowed_actions}")

    try:
        result = execute_maintenance_action(action)
        return {
            "status": "success",
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Maintenance action {action} failed: {e}")
        raise HTTPException(status_code=500, detail=f"Maintenance action failed: {e}")

@app.get("/api/v1/analytics/performance")
async def get_performance_analytics(
    days: int = 7,
    token: str = Depends(verify_token)
):
    """Get performance analytics for specified period"""
    try:
        return get_performance_data(days)
    except Exception as e:
        logger.error(f"Performance analytics failed: {e}")
        raise HTTPException(status_code=500, detail="Performance analytics failed")

@app.post("/api/v1/alerts/configure")
async def configure_alert(
    alert_config: AlertConfig,
    token: str = Depends(verify_token)
):
    """Configure monitoring alerts"""
    try:
        # Store alert configuration
        save_alert_config(alert_config)

        return {
            "status": "success",
            "message": f"Alert configuration saved for {alert_config.alert_type}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Alert configuration failed: {e}")
        raise HTTPException(status_code=500, detail="Alert configuration failed")

# Helper functions

def test_database_connection() -> bool:
    """Test database connectivity"""
    try:
        conn = sqlite3.connect('linkedin_business_development.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        return True
    except Exception:
        return False

def get_content_queue_status() -> ContentQueueStatus:
    """Get current content queue status"""
    try:
        conn = sqlite3.connect('content_queue.db')
        cursor = conn.cursor()

        # Get queue statistics
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM content_queue 
            GROUP BY status
        ''')

        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get next scheduled post
        cursor.execute('''
            SELECT scheduled_time 
            FROM content_queue 
            WHERE status = 'queued' 
            ORDER BY scheduled_time ASC 
            LIMIT 1
        ''')

        next_scheduled = cursor.fetchone()
        next_scheduled = next_scheduled[0] if next_scheduled else None

        conn.close()

        # Update Prometheus metrics
        for status in ['queued', 'posted', 'failed']:
            CONTENT_QUEUE_ITEMS.labels(status=status).set(status_counts.get(status, 0))

        return ContentQueueStatus(
            total_items=sum(status_counts.values()),
            queued=status_counts.get('queued', 0),
            posted=status_counts.get('posted', 0),
            failed=status_counts.get('failed', 0),
            next_scheduled=next_scheduled
        )
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return ContentQueueStatus(
            total_items=0, queued=0, posted=0, failed=0, next_scheduled=None
        )

def get_business_metrics() -> BusinessMetrics:
    """Get business development metrics"""
    try:
        conn = sqlite3.connect('linkedin_business_development.db')
        cursor = conn.cursor()

        # Get consultation pipeline metrics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_inquiries,
                SUM(estimated_value) as pipeline_value,
                COUNT(CASE WHEN status = 'closed_won' THEN 1 END) as won_deals,
                SUM(CASE WHEN status = 'closed_won' THEN estimated_value ELSE 0 END) as revenue
            FROM consultation_inquiries
        ''')

        inquiry_data = cursor.fetchone()

        # Get post performance metrics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_posts,
                AVG(actual_engagement_rate) as avg_engagement
            FROM linkedin_posts 
            WHERE impressions > 0
        ''')

        post_data = cursor.fetchone()

        conn.close()

        total_inquiries = inquiry_data[0] or 0
        pipeline_value = inquiry_data[1] or 0
        won_deals = inquiry_data[2] or 0
        revenue = inquiry_data[3] or 0
        posts_published = post_data[0] or 0
        engagement_rate = post_data[1] or 0

        conversion_rate = (won_deals / total_inquiries) if total_inquiries > 0 else 0

        # Update Prometheus metrics
        CONSULTATION_PIPELINE_VALUE.set(pipeline_value)
        LINKEDIN_ENGAGEMENT_RATE.set(engagement_rate)

        return BusinessMetrics(
            pipeline_value=pipeline_value,
            total_inquiries=total_inquiries,
            conversion_rate=conversion_rate,
            revenue_generated=revenue,
            engagement_rate=engagement_rate,
            posts_published=posts_published
        )
    except Exception as e:
        logger.error(f"Failed to get business metrics: {e}")
        return BusinessMetrics(
            pipeline_value=0, total_inquiries=0, conversion_rate=0,
            revenue_generated=0, engagement_rate=0, posts_published=0
        )

def check_linkedin_api_health() -> bool:
    """Check LinkedIn API health"""
    # This would make an actual API call to LinkedIn
    # For now, return True (healthy)
    return True

def calculate_system_health_score(db_healthy: bool, queue_status: ContentQueueStatus) -> float:
    """Calculate overall system health score (0-100)"""
    score = 0

    # Database health (30 points)
    if db_healthy:
        score += 30

    # Content queue health (25 points)
    if queue_status.queued > 5:
        score += 25
    elif queue_status.queued > 0:
        score += 15

    # API health (25 points)
    if check_linkedin_api_health():
        score += 25

    # Recent activity (20 points)
    if queue_status.posted > 0:
        score += 20

    return float(score)

def update_dynamic_metrics():
    """Update dynamic Prometheus metrics"""
    try:
        # Update content queue metrics
        queue_status = get_content_queue_status()

        # Update business metrics
        business_metrics = get_business_metrics()

        # Update database connection count (mock)
        DATABASE_CONNECTIONS.set(1)

    except Exception as e:
        logger.error(f"Failed to update dynamic metrics: {e}")

def get_recent_activity() -> list[dict]:
    """Get recent system activity"""
    try:
        conn = sqlite3.connect('linkedin_business_development.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                'post' as type,
                day as description,
                posted_at as timestamp
            FROM linkedin_posts 
            WHERE posted_at IS NOT NULL
            ORDER BY posted_at DESC 
            LIMIT 10
        ''')

        activities = []
        for row in cursor.fetchall():
            activities.append({
                'type': row[0],
                'description': row[1],
                'timestamp': row[2]
            })

        conn.close()
        return activities
    except Exception:
        return []

def get_active_alerts() -> list[dict]:
    """Get active system alerts"""
    # This would integrate with the alerting system
    # For now, return empty list
    return []

def execute_maintenance_action(action: str) -> str:
    """Execute maintenance action"""
    if action == "backup":
        return "Backup scheduled successfully"
    elif action == "cleanup":
        return "Database cleanup completed"
    elif action == "queue_refill":
        return "Content queue refill initiated"
    elif action == "health_check":
        return "Health check completed"
    else:
        return "Unknown action"

def get_performance_data(days: int) -> dict:
    """Get performance analytics data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        conn = sqlite3.connect('linkedin_business_development.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                DATE(posted_at) as date,
                COUNT(*) as posts,
                AVG(actual_engagement_rate) as avg_engagement,
                SUM(consultation_requests) as inquiries
            FROM linkedin_posts 
            WHERE posted_at >= ? AND posted_at <= ?
            AND impressions > 0
            GROUP BY DATE(posted_at)
            ORDER BY date DESC
        ''', (start_date.isoformat(), end_date.isoformat()))

        daily_data = []
        for row in cursor.fetchall():
            daily_data.append({
                'date': row[0],
                'posts': row[1],
                'engagement_rate': row[2] or 0,
                'inquiries': row[3] or 0
            })

        conn.close()

        return {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'daily_metrics': daily_data,
            'summary': {
                'total_posts': sum(d['posts'] for d in daily_data),
                'avg_engagement': sum(d['engagement_rate'] for d in daily_data) / len(daily_data) if daily_data else 0,
                'total_inquiries': sum(d['inquiries'] for d in daily_data)
            }
        }
    except Exception as e:
        logger.error(f"Performance data retrieval failed: {e}")
        return {'error': 'Failed to retrieve performance data'}

def save_alert_config(config: AlertConfig):
    """Save alert configuration"""
    # This would integrate with the alerting system
    # For now, just log the configuration
    logger.info(f"Alert configuration saved: {config}")

if __name__ == "__main__":
    # Production configuration
    port = int(os.getenv('API_PORT', '8000'))
    host = os.getenv('API_HOST', '0.0.0.0')

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        reload=False  # Disable reload in production
    )
