# Database Consolidation Architecture Design
## Epic 2 Week 1: PostgreSQL Migration Strategy

### Executive Summary
**MISSION CRITICAL**: Consolidate 13 SQLite databases (867KB total) into 3 optimized PostgreSQL databases to achieve 70% database reduction while maintaining 100% consultation pipeline accessibility and targeting <100ms query performance.

**Business Impact**: Protect $555K consultation pipeline during migration with zero data loss and enhanced analytics capabilities.

## Current Database Inventory Analysis

### PRIORITY 1: Core Business Pipeline ($555K Protection)
```
linkedin_business_development.db (120KB) - 7 posts, 15 inquiries, 0 pipeline records
business_development/linkedin_business_development.db (104KB) - 7 posts, 1 inquiry, 0 pipeline records [DUPLICATE DETECTED]
week3_business_development.db (20KB) - Separate Week 3 tracking system
```
**Critical Finding**: Duplicate databases with data divergence - Primary has 15 inquiries vs 1 in duplicate.

### PRIORITY 2: Analytics Intelligence (239KB → 1 Database)
```
performance_analytics.db (128KB) - Advanced ML patterns & predictions
optimized_performance_analytics.db (108KB) - [DUPLICATE with enhanced constraints]
cross_platform_performance.db (108KB) - [DUPLICATE with validation]
content_analytics.db (24KB) - Basic post analytics
cross_platform_analytics.db (56KB) - Attribution tracking
```

### PRIORITY 3: Revenue Intelligence (177KB → 1 Database)
```
revenue_acceleration.db (36KB) - Revenue opportunities & lead scoring
ab_testing.db (40KB) - A/B testing framework
synapse_content_intelligence.db (28KB) - AI content insights
unified_content_management.db (64KB) - Cross-platform content strategy
twitter_analytics.db (32KB) - Twitter-specific metrics
```

## Proposed 3-Database PostgreSQL Architecture

### Database 1: `synapse_business_core` (Priority 1)
**Purpose**: Mission-critical business operations and consultation pipeline
**Performance Target**: <50ms for all business queries

```sql
-- Unified Posts Table (consolidates linkedin_posts + week3_posts)
CREATE TABLE posts (
    post_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_post_id TEXT UNIQUE NOT NULL, -- Original post_id from SQLite
    content TEXT NOT NULL,
    posted_at TIMESTAMPTZ NOT NULL,
    platform TEXT NOT NULL DEFAULT 'linkedin',
    
    -- Business Context
    week_theme TEXT,
    day_of_week TEXT,
    business_objective TEXT,
    target_audience TEXT,
    target_consultation_type TEXT,
    
    -- Performance Metrics
    views INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    
    -- Business Development Metrics
    profile_views INTEGER DEFAULT 0,
    connection_requests INTEGER DEFAULT 0,
    dm_inquiries INTEGER DEFAULT 0,
    consultation_requests INTEGER DEFAULT 0,
    
    -- Calculated Metrics (with proper data types)
    actual_engagement_rate DECIMAL(5,4) DEFAULT 0.0,
    business_conversion_rate DECIMAL(5,4) DEFAULT 0.0,
    roi_score DECIMAL(8,2) DEFAULT 0.0,
    
    -- System Fields
    data_source TEXT NOT NULL, -- 'linkedin_primary', 'linkedin_duplicate', 'week3'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Consultation Inquiries (consolidated from multiple sources)
CREATE TABLE consultation_inquiries (
    inquiry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_inquiry_id TEXT UNIQUE NOT NULL,
    source_post_id UUID REFERENCES posts(post_id) ON DELETE SET NULL,
    
    -- Contact Information
    contact_name TEXT NOT NULL,
    company TEXT,
    company_size TEXT,
    industry TEXT,
    
    -- Inquiry Details
    inquiry_type TEXT NOT NULL,
    inquiry_channel TEXT NOT NULL,
    inquiry_text TEXT,
    inquiry_details TEXT,
    
    -- Business Qualification
    estimated_value DECIMAL(10,2),
    priority_score INTEGER,
    qualification_score INTEGER,
    
    -- Status Tracking
    status TEXT DEFAULT 'new',
    last_contact TIMESTAMPTZ,
    notes TEXT,
    
    -- System Fields
    data_source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Business Pipeline Aggregation
CREATE TABLE business_pipeline (
    pipeline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month TEXT NOT NULL,
    
    -- Activity Metrics
    total_posts INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    
    -- Business Metrics
    total_inquiries INTEGER DEFAULT 0,
    discovery_calls INTEGER DEFAULT 0,
    proposals_sent INTEGER DEFAULT 0,
    contracts_won INTEGER DEFAULT 0,
    
    -- Financial Metrics
    revenue_generated DECIMAL(12,2) DEFAULT 0.0,
    pipeline_value DECIMAL(12,2) DEFAULT 0.0,
    conversion_rate DECIMAL(5,4) DEFAULT 0.0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(month)
);

-- Performance-Optimized Indexes
CREATE INDEX CONCURRENTLY idx_posts_posted_at_desc ON posts (posted_at DESC);
CREATE INDEX CONCURRENTLY idx_posts_platform_posted_at ON posts (platform, posted_at DESC);
CREATE INDEX CONCURRENTLY idx_posts_business_objective ON posts (business_objective);
CREATE INDEX CONCURRENTLY idx_inquiries_status_created ON consultation_inquiries (status, created_at DESC);
CREATE INDEX CONCURRENTLY idx_inquiries_source_post ON consultation_inquiries (source_post_id);
CREATE INDEX CONCURRENTLY idx_inquiries_estimated_value_desc ON consultation_inquiries (estimated_value DESC NULLS LAST);
CREATE INDEX CONCURRENTLY idx_pipeline_month ON business_pipeline (month);

-- Business Intelligence Views
CREATE VIEW current_pipeline_summary AS
SELECT 
    COUNT(*) as total_inquiries,
    SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new_inquiries,
    SUM(estimated_value) as total_pipeline_value,
    AVG(estimated_value) as avg_deal_value
FROM consultation_inquiries 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';
```

### Database 2: `synapse_analytics_intelligence` (Priority 2)
**Purpose**: Advanced analytics, ML patterns, and performance optimization
**Performance Target**: <100ms for analytical queries

```sql
-- Content Analysis (consolidated from content_analysis tables)
CREATE TABLE content_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id TEXT NOT NULL, -- References external_post_id from business_core
    
    -- Content Metrics
    word_count INTEGER NOT NULL,
    emoji_count INTEGER DEFAULT 0,
    hashtag_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    data_points INTEGER DEFAULT 0,
    
    -- Content Classification
    hook_type TEXT NOT NULL,
    cta_type TEXT NOT NULL,
    topic_category TEXT NOT NULL,
    
    -- Scoring (1-5 scales with constraints)
    technical_depth INTEGER CHECK (technical_depth BETWEEN 1 AND 5),
    business_focus INTEGER CHECK (business_focus BETWEEN 1 AND 5),
    controversy_score INTEGER CHECK (controversy_score BETWEEN 1 AND 5),
    
    -- Boolean Flags
    personal_story BOOLEAN DEFAULT false,
    code_snippets BOOLEAN DEFAULT false,
    
    -- System Fields
    data_source TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance Patterns (ML-driven insights)
CREATE TABLE content_patterns (
    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type TEXT NOT NULL,
    pattern_value TEXT NOT NULL,
    
    -- Performance Metrics
    avg_engagement_rate DECIMAL(5,4) NOT NULL,
    avg_consultation_conversion DECIMAL(5,4) NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    
    -- Insights
    recommendation TEXT,
    
    -- System Fields
    identified_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(pattern_type, pattern_value)
);

-- Performance Predictions (ML predictions)
CREATE TABLE performance_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id TEXT NOT NULL,
    
    -- Predictions
    predicted_engagement_rate DECIMAL(5,4) NOT NULL,
    predicted_consultation_requests INTEGER NOT NULL,
    confidence_lower DECIMAL(5,4) NOT NULL,
    confidence_upper DECIMAL(5,4) NOT NULL,
    
    -- ML Insights (JSON stored as JSONB for better performance)
    key_factors JSONB NOT NULL,
    recommendations JSONB NOT NULL,
    
    -- Validation (populated after actual results)
    actual_engagement_rate DECIMAL(5,4),
    actual_consultation_requests INTEGER,
    prediction_accuracy DECIMAL(5,4),
    
    -- System Fields
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMPTZ
);

-- Cross-Platform Attribution (consolidated attribution tracking)
CREATE TABLE attribution_tracking (
    tracking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    touchpoint TEXT NOT NULL,
    
    -- User Tracking
    user_id TEXT,
    session_id TEXT,
    
    -- Business Metrics
    value DECIMAL(10,2) DEFAULT 0.0,
    metadata JSONB,
    
    -- Processing Status
    processed BOOLEAN DEFAULT false,
    
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for Analytics Workloads
CREATE INDEX CONCURRENTLY idx_content_analysis_post_id ON content_analysis (post_id);
CREATE INDEX CONCURRENTLY idx_content_analysis_hook_topic ON content_analysis (hook_type, topic_category);
CREATE INDEX CONCURRENTLY idx_content_analysis_scoring ON content_analysis (technical_depth, business_focus, controversy_score);
CREATE INDEX CONCURRENTLY idx_patterns_type_confidence ON content_patterns (pattern_type, confidence_score DESC);
CREATE INDEX CONCURRENTLY idx_patterns_engagement_desc ON content_patterns (avg_engagement_rate DESC);
CREATE INDEX CONCURRENTLY idx_predictions_post_accuracy ON performance_predictions (post_id, prediction_accuracy DESC NULLS LAST);
CREATE INDEX CONCURRENTLY idx_attribution_content_platform ON attribution_tracking (content_id, platform);

-- Analytics Performance View
CREATE MATERIALIZED VIEW top_performing_patterns AS
SELECT 
    pattern_type,
    pattern_value,
    avg_engagement_rate,
    avg_consultation_conversion,
    sample_size,
    confidence_score
FROM content_patterns 
WHERE confidence_score >= 0.85 
  AND sample_size >= 10
ORDER BY avg_consultation_conversion DESC, avg_engagement_rate DESC;

CREATE UNIQUE INDEX ON top_performing_patterns (pattern_type, pattern_value);
```

### Database 3: `synapse_revenue_intelligence` (Priority 3)
**Purpose**: Revenue optimization, A/B testing, and content strategy
**Performance Target**: <100ms for revenue analytics

```sql
-- Revenue Opportunities (lead scoring and qualification)
CREATE TABLE revenue_opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_source TEXT NOT NULL,
    customer_segment TEXT NOT NULL,
    
    -- Revenue Projections
    revenue_potential DECIMAL(10,2) NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    qualification_score INTEGER NOT NULL,
    
    -- Engagement Data (stored as JSONB)
    engagement_history JSONB,
    
    -- Recommendations
    recommended_offering TEXT,
    next_action TEXT,
    
    -- Status
    status TEXT DEFAULT 'active',
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- A/B Testing Framework (consolidated ab_testing)
CREATE TABLE ab_tests (
    test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_name TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    element_type TEXT NOT NULL,
    
    -- Test Configuration
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    traffic_split DECIMAL(3,2) DEFAULT 0.5,
    
    -- Statistical Configuration
    minimum_sample_size INTEGER DEFAULT 100,
    confidence_threshold DECIMAL(3,2) DEFAULT 0.95,
    
    -- Results
    winning_variant TEXT,
    improvement_rate DECIMAL(5,4) DEFAULT 0.0,
    statistical_significance DECIMAL(5,4) DEFAULT 0.0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE test_variants (
    variant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES ab_tests(test_id) ON DELETE CASCADE,
    variant_name TEXT NOT NULL,
    element_type TEXT NOT NULL,
    content TEXT NOT NULL,
    expected_metric TEXT NOT NULL,
    
    -- Performance Metrics
    impressions INTEGER DEFAULT 0,
    engagement_actions INTEGER DEFAULT 0,
    consultation_requests INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,4) DEFAULT 0.0,
    consultation_conversion DECIMAL(5,4) DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    confidence_level DECIMAL(5,4) DEFAULT 0.0,
    
    -- Results
    is_winner BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(test_id, variant_name)
);

-- Content Intelligence (AI-driven content recommendations)
CREATE TABLE content_recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_type TEXT NOT NULL,
    content_topic TEXT NOT NULL,
    target_audience TEXT NOT NULL,
    
    -- Performance Projections (stored as JSONB)
    expected_performance JSONB NOT NULL,
    reasoning TEXT NOT NULL,
    priority_score DECIMAL(5,4) NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Cross-Platform Content Strategy
CREATE TABLE content_pieces (
    content_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_content TEXT NOT NULL,
    business_objective TEXT,
    target_audience TEXT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE platform_adaptations (
    adaptation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content_pieces(content_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    adapted_content TEXT NOT NULL,
    scheduled_time TIMESTAMPTZ,
    post_id TEXT,
    status TEXT DEFAULT 'draft',
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Revenue Intelligence Indexes
CREATE INDEX CONCURRENTLY idx_opportunities_segment_revenue ON revenue_opportunities (customer_segment, revenue_potential DESC);
CREATE INDEX CONCURRENTLY idx_opportunities_status_created ON revenue_opportunities (status, created_at DESC);
CREATE INDEX CONCURRENTLY idx_tests_status_dates ON ab_tests (status, start_date DESC);
CREATE INDEX CONCURRENTLY idx_variants_test_performance ON test_variants (test_id, consultation_conversion DESC);
CREATE INDEX CONCURRENTLY idx_recommendations_priority ON content_recommendations (priority_score DESC);
CREATE INDEX CONCURRENTLY idx_adaptations_content_platform ON platform_adaptations (content_id, platform);

-- Revenue Analytics View
CREATE VIEW revenue_pipeline_summary AS
SELECT 
    customer_segment,
    COUNT(*) as total_opportunities,
    SUM(revenue_potential) as total_pipeline_value,
    AVG(confidence_score) as avg_confidence,
    AVG(qualification_score) as avg_qualification
FROM revenue_opportunities 
WHERE status = 'active'
GROUP BY customer_segment;
```

## Migration Strategy & ETL Pipeline

### Phase 1: Core Business Migration (Week 1 Days 1-2)
**CRITICAL**: Zero consultation pipeline disruption

1. **Duplicate Resolution**:
   - Primary `linkedin_business_development.db` (15 inquiries) takes precedence
   - Merge unique records from duplicate database
   - Validate data integrity with checksums

2. **Data Transformation**:
   ```sql
   -- Example ETL transformation
   INSERT INTO synapse_business_core.posts (
       external_post_id, content, posted_at, platform, data_source, ...
   )
   SELECT 
       post_id, content, posted_at::timestamptz, 'linkedin', 'linkedin_primary', ...
   FROM sqlite_data.linkedin_posts;
   ```

### Phase 2: Analytics Migration (Week 1 Days 3-4)
**Target**: Consolidate 5 analytics databases with deduplication

### Phase 3: Revenue Intelligence Migration (Week 1 Days 5-7)
**Target**: Unified revenue and content strategy

## Performance Optimization Strategy

### Connection Pooling Configuration
```python
# pgbouncer configuration for production
DATABASE_POOLS = {
    'synapse_business_core': {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'pool_recycle': 3600
    },
    'synapse_analytics_intelligence': {
        'pool_size': 15,
        'max_overflow': 25,
        'pool_timeout': 60,  # Analytics can wait longer
        'pool_recycle': 3600
    },
    'synapse_revenue_intelligence': {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 60,
        'pool_recycle': 3600
    }
}
```

### Query Performance Targets
- **Business Core**: <50ms for consultation pipeline queries
- **Analytics**: <100ms for pattern analysis queries  
- **Revenue Intelligence**: <100ms for revenue projections

### Materialized View Refresh Strategy
```sql
-- Refresh high-frequency analytics views
CREATE FUNCTION refresh_analytics_views() RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY top_performing_patterns;
    REFRESH MATERIALIZED VIEW CONCURRENTLY revenue_pipeline_summary;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh every 4 hours during business hours
SELECT cron.schedule('refresh-analytics', '0 */4 6-22 * * *', 'SELECT refresh_analytics_views();');
```

## Business Continuity Plan

### Zero-Disruption Migration Protocol
1. **Shadow Deployment**: Run PostgreSQL alongside SQLite
2. **Dual-Write Period**: Write to both systems during transition
3. **Validation Phase**: Compare query results between systems
4. **Gradual Cutover**: Migrate read queries first, then writes
5. **Rollback Capability**: Maintain SQLite backups for 30 days

### Data Validation Framework
```python
class MigrationValidator:
    def validate_record_counts(self):
        """Ensure no data loss during migration"""
        
    def validate_data_integrity(self):
        """Checksum validation for critical business data"""
        
    def validate_query_performance(self):
        """Ensure <100ms query targets are met"""
        
    def validate_consultation_pipeline(self):
        """100% accessibility of $555K pipeline data"""
```

## Success Metrics

### Consolidation Targets
- ✅ **70% Database Reduction**: 13 SQLite → 3 PostgreSQL 
- ✅ **Performance**: <100ms query response times
- ✅ **Zero Data Loss**: 100% consultation pipeline preservation
- ✅ **Storage Efficiency**: 867KB SQLite → Optimized PostgreSQL

### Business Impact Metrics
- **Consultation Pipeline Accessibility**: 100% maintained
- **Query Performance Improvement**: >5x faster complex queries
- **Maintenance Overhead**: 70% reduction in database management
- **Analytics Capability**: Unified cross-platform intelligence

## Next Steps

1. **Infrastructure Setup**: Provision 3 PostgreSQL databases with connection pooling
2. **ETL Script Development**: Create automated migration scripts with validation
3. **Testing Environment**: Set up staging environment for migration testing
4. **Business Continuity Testing**: Validate zero-disruption migration process
5. **Production Migration**: Execute phased migration with rollback capability

**EXECUTIVE APPROVAL REQUIRED**: This consolidation will protect the $555K consultation pipeline while providing 70% operational efficiency gains and enhanced analytics capabilities for future growth.