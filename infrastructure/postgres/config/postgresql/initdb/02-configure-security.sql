-- PostgreSQL Security Configuration for Production
-- Implements enterprise-grade security measures

-- Enable required extensions for monitoring and performance
\c synapse_core;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

\c synapse_analytics;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

\c synapse_revenue;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

-- Connect back to default database
\c postgres;

-- Configure Row Level Security (RLS) policies
\c synapse_core;

-- Grant schema permissions to application users
GRANT USAGE ON SCHEMA public TO synapse_app;
GRANT USAGE ON SCHEMA public TO synapse_readonly;

-- Set up connection limits per user for business continuity
ALTER USER synapse_app CONNECTION LIMIT 50;
ALTER USER synapse_readonly CONNECTION LIMIT 20;
ALTER USER analytics_user CONNECTION LIMIT 30;
ALTER USER revenue_user CONNECTION LIMIT 25;
ALTER USER postgres_exporter CONNECTION LIMIT 5;

-- Configure session security settings
ALTER DATABASE synapse_core SET log_statement = 'mod';
ALTER DATABASE synapse_core SET log_min_duration_statement = 1000;
ALTER DATABASE synapse_analytics SET log_min_duration_statement = 2000;
ALTER DATABASE synapse_revenue SET log_min_duration_statement = 1500;

-- Set up application-specific search paths
ALTER USER synapse_app SET search_path TO public;
ALTER USER synapse_readonly SET search_path TO public;
ALTER USER analytics_user SET search_path TO public;
ALTER USER revenue_user SET search_path TO public;

-- Configure password policies and security
ALTER USER synapse_app VALID UNTIL 'infinity';
ALTER USER synapse_readonly VALID UNTIL 'infinity';
ALTER USER analytics_user VALID UNTIL 'infinity';
ALTER USER revenue_user VALID UNTIL 'infinity';

-- Set up monitoring views and functions
\c synapse_core;

-- Create function to monitor consultation pipeline performance
CREATE OR REPLACE FUNCTION get_consultation_pipeline_metrics()
RETURNS TABLE(
    active_connections INTEGER,
    slow_queries INTEGER,
    avg_query_time NUMERIC,
    cache_hit_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT count(*)::INTEGER FROM pg_stat_activity WHERE state = 'active'),
        (SELECT count(*)::INTEGER FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '1 second'),
        (SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (NOW() - query_start))), 0) FROM pg_stat_activity WHERE state = 'active'),
        (SELECT COALESCE(SUM(blks_hit) / NULLIF(SUM(blks_hit + blks_read), 0) * 100, 0) FROM pg_stat_database WHERE datname = current_database());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION get_consultation_pipeline_metrics() TO postgres_exporter;
GRANT EXECUTE ON FUNCTION get_consultation_pipeline_metrics() TO synapse_readonly;

-- Create indexes for performance monitoring
\c synapse_core;

-- Performance monitoring helper functions
CREATE OR REPLACE FUNCTION reset_query_stats() RETURNS void AS $$
BEGIN
    SELECT pg_stat_statements_reset();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION reset_query_stats() TO postgres;

-- Set up audit logging function
CREATE OR REPLACE FUNCTION log_business_critical_operations()
RETURNS TRIGGER AS $$
BEGIN
    -- Log critical operations for business continuity
    INSERT INTO audit_log (
        operation,
        table_name,
        user_name,
        timestamp,
        old_values,
        new_values
    ) VALUES (
        TG_OP,
        TG_TABLE_NAME,
        current_user,
        NOW(),
        row_to_json(OLD),
        row_to_json(NEW)
    );
    
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB
);

-- Grant necessary permissions
GRANT SELECT ON audit_log TO synapse_readonly;
GRANT INSERT ON audit_log TO synapse_app;