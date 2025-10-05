-- ============================================================================
-- ANALYTICS DATABASE CONSOLIDATION SCHEMA
-- Epic 2 Week 1: 11 SQLite Analytics DBs → 1 PostgreSQL Analytics Database
-- ============================================================================

-- Connect to synapse_analytics database
\c synapse_analytics;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Set timezone for consistent timestamps
SET timezone = 'UTC';

-- ============================================================================
-- CONTENT ANALYTICS TABLES
-- ============================================================================

-- Consolidated Posts Table (from content_analytics.db)
CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    day_of_week TEXT,
    content_type TEXT,
    signature_series TEXT,
    headline TEXT,
    platform TEXT NOT NULL DEFAULT 'linkedin',
    posting_time TIME,
    content TEXT,
    views INTEGER DEFAULT 0 CHECK (views >= 0),
    likes INTEGER DEFAULT 0 CHECK (likes >= 0),
    comments INTEGER DEFAULT 0 CHECK (comments >= 0),
    shares INTEGER DEFAULT 0 CHECK (shares >= 0),
    saves INTEGER DEFAULT 0 CHECK (saves >= 0),
    engagement_rate DECIMAL(5,2) CHECK (engagement_rate >= 0),
    profile_views INTEGER DEFAULT 0 CHECK (profile_views >= 0),
    connection_requests INTEGER DEFAULT 0 CHECK (connection_requests >= 0),
    consultation_inquiries INTEGER DEFAULT 0 CHECK (consultation_inquiries >= 0),
    discovery_calls INTEGER DEFAULT 0 CHECK (discovery_calls >= 0),
    click_through_rate DECIMAL(5,2) CHECK (click_through_rate >= 0),
    comment_quality_score DECIMAL(3,2) CHECK (comment_quality_score >= 0),
    business_relevance_score DECIMAL(3,2) CHECK (business_relevance_score >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Weekly Performance Aggregation (from content_analytics.db)
CREATE TABLE weekly_performance (
    performance_id SERIAL PRIMARY KEY,
    week_number INTEGER NOT NULL,
    start_date DATE NOT NULL,
    quarter TEXT,
    theme TEXT,
    total_posts INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2),
    total_profile_views INTEGER DEFAULT 0,
    total_connections INTEGER DEFAULT 0,
    total_inquiries INTEGER DEFAULT 0,
    total_discovery_calls INTEGER DEFAULT 0,
    best_performing_post TEXT,
    best_engagement_rate DECIMAL(5,2),
    optimal_posting_time TIME,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(week_number, start_date)
);

-- Business Pipeline Tracking (from content_analytics.db)
CREATE TABLE business_pipeline (
    inquiry_id TEXT PRIMARY KEY,
    source_post_id TEXT REFERENCES posts(post_id),
    inquiry_date DATE NOT NULL,
    inquiry_type TEXT,
    company_size TEXT,
    industry TEXT,
    project_value INTEGER CHECK (project_value >= 0),
    status TEXT CHECK (status IN ('new', 'qualified', 'contacted', 'proposal', 'closed_won', 'closed_lost')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- PERFORMANCE ANALYTICS TABLES
-- ============================================================================

-- Content Patterns Analysis (from performance_analytics.db)
CREATE TABLE content_patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    pattern_value TEXT NOT NULL,
    avg_engagement_rate DECIMAL(5,2),
    avg_consultation_conversion DECIMAL(5,2),
    sample_size INTEGER DEFAULT 0,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    recommendation TEXT,
    identified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Predictions (from performance_analytics.db)
CREATE TABLE performance_predictions (
    prediction_id TEXT PRIMARY KEY,
    post_id TEXT REFERENCES posts(post_id),
    predicted_engagement_rate DECIMAL(5,2),
    predicted_consultation_requests INTEGER,
    confidence_lower DECIMAL(5,2),
    confidence_upper DECIMAL(5,2),
    key_factors JSONB,
    recommendations TEXT,
    actual_engagement_rate DECIMAL(5,2),
    actual_consultation_requests INTEGER,
    prediction_accuracy DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Content Analysis (from performance_analytics.db)
CREATE TABLE content_analysis (
    analysis_id TEXT PRIMARY KEY,
    post_id TEXT REFERENCES posts(post_id),
    word_count INTEGER,
    hook_type TEXT,
    cta_type TEXT,
    topic_category TEXT,
    technical_depth INTEGER CHECK (technical_depth >= 0 AND technical_depth <= 10),
    business_focus INTEGER CHECK (business_focus >= 0 AND business_focus <= 10),
    controversy_score DECIMAL(3,2) CHECK (controversy_score >= 0 AND controversy_score <= 1),
    emoji_count INTEGER DEFAULT 0,
    hashtag_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    personal_story BOOLEAN DEFAULT FALSE,
    data_points INTEGER DEFAULT 0,
    code_snippets INTEGER DEFAULT 0,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Metrics Aggregation (from performance_analytics.db)
CREATE TABLE performance_metrics_agg (
    metric_id TEXT PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_date DATE NOT NULL,
    total_posts INTEGER DEFAULT 0,
    avg_engagement_rate DECIMAL(5,2),
    total_consultations INTEGER DEFAULT 0,
    top_performing_pattern TEXT,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- REVENUE ANALYTICS TABLES
-- ============================================================================

-- Revenue Opportunities (from revenue_acceleration.db)
CREATE TABLE revenue_opportunities (
    opportunity_id TEXT PRIMARY KEY,
    lead_source TEXT,
    customer_segment TEXT,
    revenue_potential INTEGER CHECK (revenue_potential >= 0),
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    qualification_score DECIMAL(3,2) CHECK (qualification_score >= 0 AND qualification_score <= 1),
    engagement_history JSONB,
    recommended_offering TEXT,
    next_action TEXT,
    status TEXT CHECK (status IN ('prospect', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Product Performance (from revenue_acceleration.db)
CREATE TABLE product_performance (
    performance_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_point INTEGER CHECK (price_point >= 0),
    monthly_sales INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,2) CHECK (conversion_rate >= 0),
    customer_ltv INTEGER CHECK (customer_ltv >= 0),
    churn_rate DECIMAL(5,2) CHECK (churn_rate >= 0),
    growth_rate DECIMAL(5,2),
    month_year TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enhanced Attribution (from revenue_acceleration.db)
CREATE TABLE enhanced_attribution (
    attribution_id TEXT PRIMARY KEY,
    customer_id TEXT,
    revenue_amount INTEGER CHECK (revenue_amount >= 0),
    content_touchpoints JSONB,
    conversion_path JSONB,
    customer_segment TEXT,
    product_purchased TEXT,
    sales_cycle_days INTEGER CHECK (sales_cycle_days >= 0),
    attribution_weights JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Lead Scoring Factors (from revenue_acceleration.db)
CREATE TABLE lead_scoring_factors (
    scoring_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    company_size_score DECIMAL(3,2) CHECK (company_size_score >= 0 AND company_size_score <= 1),
    role_authority_score DECIMAL(3,2) CHECK (role_authority_score >= 0 AND role_authority_score <= 1),
    engagement_score DECIMAL(3,2) CHECK (engagement_score >= 0 AND engagement_score <= 1),
    urgency_indicators DECIMAL(3,2) CHECK (urgency_indicators >= 0 AND urgency_indicators <= 1),
    content_consumption_score DECIMAL(3,2) CHECK (content_consumption_score >= 0 AND content_consumption_score <= 1),
    social_proof_score DECIMAL(3,2) CHECK (social_proof_score >= 0 AND social_proof_score <= 1),
    budget_authority_score DECIMAL(3,2) CHECK (budget_authority_score >= 0 AND budget_authority_score <= 1),
    total_score DECIMAL(3,2) CHECK (total_score >= 0 AND total_score <= 1),
    segment_classification TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- A/B TESTING TABLES
-- ============================================================================

-- A/B Tests (from ab_testing.db)
CREATE TABLE ab_tests (
    test_id TEXT PRIMARY KEY,
    test_name TEXT NOT NULL,
    hypothesis TEXT,
    element_type TEXT NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    status TEXT CHECK (status IN ('planned', 'active', 'completed', 'cancelled')),
    traffic_split JSONB,
    minimum_sample_size INTEGER CHECK (minimum_sample_size > 0),
    confidence_threshold DECIMAL(3,2) CHECK (confidence_threshold >= 0 AND confidence_threshold <= 1),
    winning_variant TEXT,
    improvement_rate DECIMAL(5,2),
    statistical_significance DECIMAL(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Test Variants (from ab_testing.db)
CREATE TABLE test_variants (
    variant_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES ab_tests(test_id) ON DELETE CASCADE,
    variant_name TEXT NOT NULL,
    element_type TEXT NOT NULL,
    content TEXT,
    expected_metric TEXT,
    impressions INTEGER DEFAULT 0 CHECK (impressions >= 0),
    engagement_actions INTEGER DEFAULT 0 CHECK (engagement_actions >= 0),
    consultation_requests INTEGER DEFAULT 0 CHECK (consultation_requests >= 0),
    engagement_rate DECIMAL(5,2) CHECK (engagement_rate >= 0),
    consultation_conversion DECIMAL(5,2) CHECK (consultation_conversion >= 0),
    sample_size INTEGER DEFAULT 0 CHECK (sample_size >= 0),
    confidence_level DECIMAL(3,2) CHECK (confidence_level >= 0 AND confidence_level <= 1),
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Test Assignments (from ab_testing.db)
CREATE TABLE test_assignments (
    assignment_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES ab_tests(test_id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL REFERENCES test_variants(variant_id) ON DELETE CASCADE,
    post_id TEXT REFERENCES posts(post_id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- CROSS-PLATFORM ANALYTICS TABLES
-- ============================================================================

-- Attribution Tracking (from cross_platform_analytics.db)
CREATE TABLE attribution_tracking (
    tracking_id TEXT PRIMARY KEY,
    content_id TEXT,
    platform TEXT NOT NULL,
    touchpoint TEXT NOT NULL,
    user_id TEXT,
    session_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    value DECIMAL(10,2),
    metadata JSONB,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ
);

-- Conversion Paths (from cross_platform_analytics.db)
CREATE TABLE conversion_paths (
    path_id TEXT PRIMARY KEY,
    user_id TEXT,
    content_id TEXT,
    touchpoints JSONB,
    conversion_value DECIMAL(10,2),
    conversion_type TEXT,
    journey_start TIMESTAMPTZ,
    journey_end TIMESTAMPTZ,
    attribution_weights JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cross-platform Performance (from cross_platform_analytics.db)
CREATE TABLE cross_platform_performance (
    performance_id TEXT PRIMARY KEY,
    content_id TEXT,
    platform TEXT NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0 CHECK (impressions >= 0),
    clicks INTEGER DEFAULT 0 CHECK (clicks >= 0),
    engagements INTEGER DEFAULT 0 CHECK (engagements >= 0),
    conversions INTEGER DEFAULT 0 CHECK (conversions >= 0),
    revenue DECIMAL(10,2) DEFAULT 0,
    assisted_conversions INTEGER DEFAULT 0 CHECK (assisted_conversions >= 0),
    attribution_revenue DECIMAL(10,2) DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Platform Interactions (from cross_platform_analytics.db)
CREATE TABLE platform_interactions (
    interaction_id TEXT PRIMARY KEY,
    user_id TEXT,
    from_platform TEXT NOT NULL,
    to_platform TEXT NOT NULL,
    content_id TEXT,
    interaction_type TEXT NOT NULL,
    time_between_seconds INTEGER CHECK (time_between_seconds >= 0),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- ADDITIONAL ANALYTICS TABLES (from other databases)
-- ============================================================================

-- Twitter Analytics (consolidated structure)
CREATE TABLE twitter_analytics (
    tweet_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    posted_at TIMESTAMPTZ NOT NULL,
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2),
    potential_leads INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unified Content Management
CREATE TABLE content_management (
    content_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL,
    status TEXT CHECK (status IN ('draft', 'scheduled', 'published', 'archived')),
    platforms JSONB,
    scheduled_date TIMESTAMPTZ,
    published_date TIMESTAMPTZ,
    performance_metrics JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Content Analytics Indexes
CREATE INDEX idx_posts_date ON posts(date);
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_content_type ON posts(content_type);
CREATE INDEX idx_weekly_performance_week ON weekly_performance(week_number);
CREATE INDEX idx_business_pipeline_status ON business_pipeline(status);
CREATE INDEX idx_business_pipeline_date ON business_pipeline(inquiry_date);

-- Performance Analytics Indexes
CREATE INDEX idx_content_patterns_type ON content_patterns(pattern_type);
CREATE INDEX idx_performance_predictions_post ON performance_predictions(post_id);
CREATE INDEX idx_content_analysis_post ON content_analysis(post_id);
CREATE INDEX idx_performance_metrics_date ON performance_metrics_agg(metric_date);

-- Revenue Analytics Indexes
CREATE INDEX idx_revenue_opportunities_status ON revenue_opportunities(status);
CREATE INDEX idx_product_performance_product ON product_performance(product_id);
CREATE INDEX idx_enhanced_attribution_customer ON enhanced_attribution(customer_id);
CREATE INDEX idx_lead_scoring_lead ON lead_scoring_factors(lead_id);

-- A/B Testing Indexes
CREATE INDEX idx_ab_tests_status ON ab_tests(status);
CREATE INDEX idx_ab_tests_dates ON ab_tests(start_date, end_date);
CREATE INDEX idx_test_variants_test ON test_variants(test_id);
CREATE INDEX idx_test_assignments_test ON test_assignments(test_id);

-- Cross-platform Indexes
CREATE INDEX idx_attribution_tracking_platform ON attribution_tracking(platform);
CREATE INDEX idx_attribution_tracking_timestamp ON attribution_tracking(timestamp);
CREATE INDEX idx_conversion_paths_user ON conversion_paths(user_id);
CREATE INDEX idx_cross_platform_performance_content ON cross_platform_performance(content_id);
CREATE INDEX idx_platform_interactions_user ON platform_interactions(user_id);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to relevant tables
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_business_pipeline_updated_at BEFORE UPDATE ON business_pipeline FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_revenue_opportunities_updated_at BEFORE UPDATE ON revenue_opportunities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ab_tests_updated_at BEFORE UPDATE ON ab_tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_management_updated_at BEFORE UPDATE ON content_management FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PARTITIONING FOR TIME-SERIES TABLES (if TimescaleDB is available)
-- ============================================================================

-- Convert time-series tables to hypertables for better performance
-- SELECT create_hypertable('attribution_tracking', 'timestamp', if_not_exists => TRUE);
-- SELECT create_hypertable('cross_platform_performance', 'date', if_not_exists => TRUE);
-- SELECT create_hypertable('performance_metrics_agg', 'metric_date', if_not_exists => TRUE);