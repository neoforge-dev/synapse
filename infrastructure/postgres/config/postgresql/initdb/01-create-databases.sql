-- Initialize PostgreSQL Databases for Synapse Production Infrastructure
-- Creates databases, users, and security configurations

-- Core Business Database Setup
CREATE DATABASE synapse_core WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Analytics Database Setup  
CREATE DATABASE synapse_analytics WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Revenue Intelligence Database Setup
CREATE DATABASE synapse_revenue WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    TEMPLATE = template0;

-- Create Application Users with Specific Privileges
-- Replication user for high availability
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'repl_secure_2024';

-- Core application user with full access to business database
CREATE USER synapse_app WITH ENCRYPTED PASSWORD 'app_secure_2024';
GRANT CONNECT ON DATABASE synapse_core TO synapse_app;
GRANT CREATE ON DATABASE synapse_core TO synapse_app;

-- Read-only user for reporting and analytics
CREATE USER synapse_readonly WITH ENCRYPTED PASSWORD 'readonly_secure_2024';
GRANT CONNECT ON DATABASE synapse_core TO synapse_readonly;

-- Analytics-specific user
CREATE USER analytics_user WITH ENCRYPTED PASSWORD 'analytics_secure_2024';
GRANT CONNECT ON DATABASE synapse_analytics TO analytics_user;
GRANT CREATE ON DATABASE synapse_analytics TO analytics_user;

-- Revenue intelligence user  
CREATE USER revenue_user WITH ENCRYPTED PASSWORD 'revenue_secure_2024';
GRANT CONNECT ON DATABASE synapse_revenue TO revenue_user;
GRANT CREATE ON DATABASE synapse_revenue TO revenue_user;

-- Monitoring user for PostgreSQL exporter
CREATE USER postgres_exporter WITH ENCRYPTED PASSWORD 'exporter_secure_2024';
GRANT CONNECT ON DATABASE synapse_core TO postgres_exporter;
GRANT CONNECT ON DATABASE synapse_analytics TO postgres_exporter;
GRANT CONNECT ON DATABASE synapse_revenue TO postgres_exporter;

-- Grant monitoring permissions
GRANT SELECT ON pg_stat_database TO postgres_exporter;
GRANT SELECT ON pg_stat_user_tables TO postgres_exporter;
GRANT SELECT ON pg_stat_user_indexes TO postgres_exporter;
GRANT SELECT ON pg_statio_user_tables TO postgres_exporter;
GRANT SELECT ON pg_stat_activity TO postgres_exporter;
GRANT SELECT ON pg_stat_replication TO postgres_exporter;