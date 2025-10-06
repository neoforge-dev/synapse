-- ============================================================================
-- ADDITIONAL ANALYTICS TABLES SCHEMA
-- Remaining databases: unified_content_management, synapse_content_intelligence,
-- week3_business_development, advanced_graph_rag_analytics, twitter_analytics
-- ============================================================================

\c synapse_analytics;

-- ============================================================================
-- TWITTER ANALYTICS TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS twitter_posts (
    tweet_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    content TEXT NOT NULL,
    thread_position INTEGER DEFAULT 1,
    total_threads INTEGER DEFAULT 1,
    impressions INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0.0,
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS twitter_threads (
    thread_id TEXT PRIMARY KEY,
    first_tweet_id TEXT REFERENCES twitter_posts(tweet_id),
    total_tweets INTEGER DEFAULT 1,
    total_impressions INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    thread_topic TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- UNIFIED CONTENT MANAGEMENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS content_pieces (
    content_id TEXT PRIMARY KEY,
    original_content TEXT NOT NULL,
    business_objective TEXT,
    target_audience TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_adaptations (
    adaptation_id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content_pieces(content_id),
    platform TEXT NOT NULL,
    adapted_content TEXT NOT NULL,
    platform_specific_optimizations JSONB,
    character_count INTEGER,
    media_requirements TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cross_platform_metrics (
    metric_id TEXT PRIMARY KEY,
    content_id TEXT REFERENCES content_pieces(content_id),
    platform TEXT NOT NULL,
    total_reach INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    consultation_attribution INTEGER DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_strategies (
    strategy_id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    business_objectives JSONB,
    target_audiences JSONB,
    success_metrics JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT CHECK (status IN ('active', 'paused', 'completed', 'archived'))
);

-- ============================================================================
-- SYNAPSE CONTENT INTELLIGENCE TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS content_insights (
    insight_id TEXT PRIMARY KEY,
    content_id TEXT,
    insight_type TEXT NOT NULL,
    insight_description TEXT,
    confidence_score DECIMAL(3,2),
    actionable_recommendations JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audience_intelligence (
    intelligence_id TEXT PRIMARY KEY,
    audience_segment TEXT NOT NULL,
    demographic_profile JSONB,
    behavioral_patterns JSONB,
    engagement_preferences JSONB,
    conversion_likelihood DECIMAL(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    recommended_topic TEXT NOT NULL,
    business_alignment_score DECIMAL(3,2),
    audience_match_score DECIMAL(3,2),
    projected_consultation_potential DECIMAL(3,2),
    content_angle_suggestions JSONB,
    optimal_timing TEXT,
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- WEEK 3 BUSINESS DEVELOPMENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS week3_posts (
    post_id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    day TEXT NOT NULL,
    title TEXT NOT NULL,
    series TEXT NOT NULL,
    posting_time TIME NOT NULL,
    business_dev_focus TEXT NOT NULL,
    target_consultation_type TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0.0,
    profile_views INTEGER DEFAULT 0,
    connection_requests INTEGER DEFAULT 0,
    consultation_inquiries INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consultation_inquiries (
    inquiry_id TEXT PRIMARY KEY,
    source_post_id TEXT REFERENCES week3_posts(post_id),
    inquiry_date DATE NOT NULL,
    inquiry_type TEXT NOT NULL,
    company_name TEXT,
    contact_name TEXT,
    company_size TEXT,
    inquiry_details TEXT,
    estimated_value DECIMAL(10,2),
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'proposal', 'won', 'lost')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- ADVANCED GRAPH RAG ANALYTICS TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS graph_insights (
    insight_id TEXT PRIMARY KEY,
    insight_type TEXT,
    insight_description TEXT,
    entities_involved JSONB,
    relationships JSONB,
    business_impact_score DECIMAL(5,2),
    confidence_score DECIMAL(3,2),
    actionable_recommendations JSONB,
    projected_pipeline_value DECIMAL(10,2),
    implementation_effort TEXT,
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'reviewed', 'implementing', 'completed', 'rejected'))
);

CREATE TABLE IF NOT EXISTS consultation_predictions (
    prediction_id TEXT PRIMARY KEY,
    content_id TEXT,
    predicted_inquiries INTEGER,
    predicted_pipeline_value DECIMAL(10,2),
    confidence_lower DECIMAL(5,2),
    confidence_upper DECIMAL(5,2),
    success_factors JSONB,
    optimization_opportunities JSONB,
    competitive_advantages JSONB,
    audience_segments JSONB,
    optimal_timing JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actual_inquiries INTEGER DEFAULT NULL,
    actual_pipeline_value DECIMAL(10,2) DEFAULT NULL,
    prediction_accuracy DECIMAL(5,2) DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS autonomous_optimizations (
    optimization_id TEXT PRIMARY KEY,
    optimization_type TEXT,
    current_performance JSONB,
    optimized_performance JSONB,
    improvement_percentage DECIMAL(5,2),
    implementation_steps JSONB,
    risk_assessment JSONB,
    expected_timeline TEXT,
    success_metrics JSONB,
    rollback_strategy TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'implementing', 'completed', 'rolled_back')),
    implementation_date TIMESTAMPTZ DEFAULT NULL,
    results JSONB DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS graph_patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_type TEXT,
    pattern_structure TEXT,
    business_context TEXT,
    success_indicators JSONB,
    frequency_score DECIMAL(5,2),
    impact_score DECIMAL(5,2),
    last_detected TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_twitter_posts_post_id ON twitter_posts(post_id);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_engagement ON twitter_posts(engagement_rate DESC);
CREATE INDEX IF NOT EXISTS idx_content_pieces_created ON content_pieces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_platform_adaptations_content ON platform_adaptations(content_id);
CREATE INDEX IF NOT EXISTS idx_platform_adaptations_platform ON platform_adaptations(platform);
CREATE INDEX IF NOT EXISTS idx_content_recommendations_priority ON content_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_week3_posts_date ON week3_posts(date);
CREATE INDEX IF NOT EXISTS idx_consultation_inquiries_status ON consultation_inquiries(status);
CREATE INDEX IF NOT EXISTS idx_graph_insights_priority ON graph_insights(priority);
CREATE INDEX IF NOT EXISTS idx_graph_insights_status ON graph_insights(status);
CREATE INDEX IF NOT EXISTS idx_consultation_predictions_content ON consultation_predictions(content_id);
CREATE INDEX IF NOT EXISTS idx_autonomous_optimizations_status ON autonomous_optimizations(status);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE TRIGGER IF NOT EXISTS update_content_pieces_updated_at
    BEFORE UPDATE ON content_pieces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_twitter_posts_updated_at
    BEFORE UPDATE ON twitter_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
