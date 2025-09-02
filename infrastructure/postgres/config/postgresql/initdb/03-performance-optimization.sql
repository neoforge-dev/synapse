-- PostgreSQL Performance Optimization for Consultation Pipeline
-- Implements indexes and optimizations for <100ms query performance

-- Connect to Core Business Database
\c synapse_core;

-- Create optimized indexes for consultation pipeline queries
-- These indexes support the critical <100ms SLA for business operations

-- User authentication and session management (frequent lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active 
ON users (email) WHERE is_active = true AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_api_key_active 
ON users (api_key) WHERE is_active = true AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_organization_active 
ON users (organization_id, is_active) WHERE deleted_at IS NULL;

-- Organization queries (multi-tenant performance)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_domain_active 
ON organizations (domain) WHERE subscription_status = 'active' AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_subscription_status 
ON organizations (subscription_status, subscription_ends_at) WHERE deleted_at IS NULL;

-- Content generation pipeline (high-volume operations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_org_created_status 
ON content_generated (organization_id, created_at DESC, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_user_type_created 
ON content_generated (user_id, content_type, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_linkedin_posted 
ON content_generated (linkedin_posted_at, status) WHERE posted_to_linkedin = true;

-- Lead detection queries (consultation pipeline critical path)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_org_detected_priority 
ON leads_detected (organization_id, detected_at DESC, priority);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_score_followup 
ON leads_detected (lead_score DESC, follow_up_status) WHERE lead_score >= 7;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_conversion_value 
ON leads_detected (converted_to_consultation, consultation_value_cents DESC) 
WHERE converted_to_consultation = true;

-- LinkedIn integration performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_linkedin_org_active 
ON linkedin_integrations (organization_id, is_active, last_sync_at) WHERE is_active = true;

-- Composite indexes for complex business queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_content_engagement_analysis 
ON content_generated (organization_id, created_at, engagement_rate, consultation_inquiries_generated) 
WHERE status = 'posted' AND posted_to_linkedin = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_pipeline_analysis 
ON leads_detected (organization_id, detected_at, lead_score, estimated_value_cents, follow_up_status);

-- Performance optimization functions
CREATE OR REPLACE FUNCTION optimize_consultation_pipeline_performance()
RETURNS void AS $$
BEGIN
    -- Update table statistics for better query planning
    ANALYZE users;
    ANALYZE organizations;  
    ANALYZE content_generated;
    ANALYZE leads_detected;
    ANALYZE linkedin_integrations;
    
    -- Log optimization completion
    INSERT INTO audit_log (operation, table_name, user_name, timestamp, new_values)
    VALUES ('OPTIMIZE', 'performance_optimization', current_user, NOW(), 
            '{"action": "consultation_pipeline_optimization_completed"}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execution to monitoring user
GRANT EXECUTE ON FUNCTION optimize_consultation_pipeline_performance() TO postgres_exporter;

-- Connect to Analytics Database
\c synapse_analytics;

-- Analytics-specific performance indexes
-- These support heavy analytical workloads without impacting core business operations

-- Time-series analytics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_events_timestamp 
ON analytics_events (timestamp DESC, event_type, organization_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_user_sessions 
ON user_sessions (organization_id, session_start DESC, session_end);

-- Revenue analytics indexes  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_metrics_period 
ON revenue_metrics (organization_id, period_start DESC, metric_type);

-- Connect to Revenue Intelligence Database
\c synapse_revenue;

-- Revenue-specific optimizations for strategic reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_pipeline_value 
ON revenue_pipeline (organization_id, created_at DESC, pipeline_value_cents DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_revenue_conversions_date 
ON revenue_conversions (conversion_date DESC, conversion_value_cents DESC);

-- Performance monitoring views
\c synapse_core;

-- Create materialized view for real-time consultation pipeline health
CREATE MATERIALIZED VIEW consultation_pipeline_health AS
SELECT 
    o.id as organization_id,
    o.name as organization_name,
    COUNT(DISTINCT u.id) as active_users,
    COUNT(DISTINCT CASE WHEN cg.created_at >= NOW() - INTERVAL '7 days' THEN cg.id END) as content_last_7_days,
    COUNT(DISTINCT CASE WHEN ld.detected_at >= NOW() - INTERVAL '7 days' THEN ld.id END) as leads_last_7_days,
    COALESCE(SUM(CASE WHEN ld.detected_at >= NOW() - INTERVAL '7 days' THEN ld.estimated_value_cents END), 0) as pipeline_value_last_7_days,
    AVG(CASE WHEN cg.created_at >= NOW() - INTERVAL '30 days' THEN cg.engagement_rate END) as avg_engagement_rate,
    COUNT(DISTINCT CASE WHEN ld.converted_to_consultation = true THEN ld.id END) as total_conversions
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id AND u.is_active = true AND u.deleted_at IS NULL
LEFT JOIN content_generated cg ON cg.organization_id = o.id 
LEFT JOIN leads_detected ld ON ld.organization_id = o.id
WHERE o.subscription_status = 'active' AND o.deleted_at IS NULL
GROUP BY o.id, o.name;

-- Create unique index on materialized view
CREATE UNIQUE INDEX ON consultation_pipeline_health (organization_id);

-- Set up automatic refresh
CREATE OR REPLACE FUNCTION refresh_consultation_pipeline_health()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY consultation_pipeline_health;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant access to monitoring and readonly users
GRANT SELECT ON consultation_pipeline_health TO synapse_readonly;
GRANT SELECT ON consultation_pipeline_health TO postgres_exporter;

-- Create function to identify performance bottlenecks
CREATE OR REPLACE FUNCTION identify_performance_bottlenecks()
RETURNS TABLE(
    query TEXT,
    avg_time NUMERIC,
    calls BIGINT,
    total_time NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pss.query,
        pss.mean_time,
        pss.calls,
        pss.total_time
    FROM pg_stat_statements pss
    WHERE pss.mean_time > 100  -- Queries taking more than 100ms average
    ORDER BY pss.total_time DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION identify_performance_bottlenecks() TO postgres_exporter;
GRANT EXECUTE ON FUNCTION identify_performance_bottlenecks() TO synapse_readonly;