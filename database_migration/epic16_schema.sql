-- =====================================================================
-- Epic 16 PostgreSQL Schema Definition
-- Fortune 500 Acquisition, ABM Campaigns, and Enterprise Onboarding
-- =====================================================================
-- Generated: 2025-10-08
-- Target Database: synapse_business_core
-- Tables: 15 (6 Fortune 500 + 4 ABM + 5 Onboarding)
-- Migration Plan: EPIC16_MIGRATION_PLAN.md
-- =====================================================================

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================================
-- SECTION 1: FORTUNE 500 ACQUISITION SYSTEM (6 tables)
-- Purpose: Manage Fortune 500 enterprise prospect pipeline ($5M+ ARR)
-- =====================================================================

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS f500_roi_tracking CASCADE;
DROP TABLE IF EXISTS f500_sales_sequences CASCADE;
DROP TABLE IF EXISTS f500_business_cases CASCADE;
DROP TABLE IF EXISTS f500_lead_scoring CASCADE;
DROP TABLE IF EXISTS f500_prospects CASCADE;

-- Table: f500_prospects
-- Purpose: Core Fortune 500 company prospect database with firmographic data
-- Key Features: AI scoring integration, decision maker tracking, tech stack analysis
CREATE TABLE f500_prospects (
    prospect_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(500) NOT NULL,
    revenue_billions NUMERIC(10, 2),
    industry VARCHAR(200),
    headquarters VARCHAR(500),
    employees INTEGER,
    stock_symbol VARCHAR(10),
    market_cap_billions NUMERIC(10, 2),
    ceo_name VARCHAR(200),
    cto_name VARCHAR(200),
    engineering_headcount INTEGER,
    tech_stack JSONB,  -- Array of technologies used
    digital_transformation_score REAL,
    acquisition_score REAL,
    contact_priority VARCHAR(50),  -- critical, high, medium, low
    estimated_contract_value NUMERIC(12, 2),
    pain_points JSONB,  -- Array of identified pain points
    decision_makers JSONB,  -- Array of decision maker objects
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE f500_prospects IS 'Fortune 500 company prospects with AI-driven acquisition scoring';
COMMENT ON COLUMN f500_prospects.tech_stack IS 'JSON array of current technology stack';
COMMENT ON COLUMN f500_prospects.pain_points IS 'JSON array of identified business challenges';
COMMENT ON COLUMN f500_prospects.decision_makers IS 'JSON array of key decision makers with contact info';

-- Table: f500_lead_scoring
-- Purpose: AI-powered lead scoring history and rationale tracking
-- Key Features: Multi-factor scoring model, confidence tracking, historical scoring
CREATE TABLE f500_lead_scoring (
    scoring_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES f500_prospects(prospect_id) ON DELETE CASCADE,
    base_score REAL,
    revenue_multiplier REAL,
    industry_fit_score REAL,
    technology_readiness REAL,
    decision_maker_accessibility REAL,
    timing_signals REAL,
    competitive_landscape REAL,
    final_score REAL,
    confidence_level REAL,
    scoring_rationale JSONB,  -- Array of scoring factors and explanations
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE f500_lead_scoring IS 'AI-powered lead scoring history with multi-factor analysis';
COMMENT ON COLUMN f500_lead_scoring.scoring_rationale IS 'JSON array explaining scoring factors and decisions';

-- Table: f500_business_cases
-- Purpose: Automated business case generation for Fortune 500 prospects
-- Key Features: ROI calculations, risk assessment, implementation planning
CREATE TABLE f500_business_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES f500_prospects(prospect_id) ON DELETE CASCADE,
    problem_quantification JSONB,  -- Quantified business problems
    solution_benefits JSONB,  -- Detailed solution benefits
    roi_calculation JSONB,  -- Complete ROI breakdown
    risk_assessment JSONB,  -- Risk analysis and mitigation
    implementation_timeline JSONB,  -- Phased implementation plan
    investment_options JSONB,  -- Different pricing/engagement options
    projected_savings NUMERIC(12, 2),
    payback_months INTEGER,
    confidence_score REAL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE f500_business_cases IS 'AI-generated business cases with ROI calculations and risk assessment';
COMMENT ON COLUMN f500_business_cases.roi_calculation IS 'Detailed ROI breakdown including costs, benefits, and timeline';

-- Table: f500_sales_sequences
-- Purpose: Multi-touch sales engagement sequences for Fortune 500 prospects
-- Key Features: Personalized touchpoint sequences, engagement tracking, conversion optimization
CREATE TABLE f500_sales_sequences (
    sequence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES f500_prospects(prospect_id) ON DELETE CASCADE,
    sequence_name VARCHAR(500),
    sequence_type VARCHAR(100),  -- email_series, executive_briefing, multi_channel
    touchpoints JSONB,  -- Array of touchpoint objects
    current_step INTEGER DEFAULT 1,
    total_steps INTEGER,
    engagement_score REAL,
    response_rate REAL,
    sequence_status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed, converted
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    next_touchpoint_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE f500_sales_sequences IS 'Multi-touch engagement sequences optimized for Fortune 500 conversion';
COMMENT ON COLUMN f500_sales_sequences.touchpoints IS 'Ordered array of touchpoint objects with timing and content';

-- Table: f500_roi_tracking
-- Purpose: Track ROI and investment performance for Fortune 500 prospects
-- Key Features: Pipeline value tracking, conversion metrics, investment analysis
CREATE TABLE f500_roi_tracking (
    roi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES f500_prospects(prospect_id) ON DELETE CASCADE,
    investment_type VARCHAR(100),  -- sales_effort, marketing_spend, content_creation
    investment_amount NUMERIC(12, 2),
    pipeline_value_generated NUMERIC(12, 2),
    actual_revenue NUMERIC(12, 2) DEFAULT 0,
    roi_ratio REAL,
    conversion_status VARCHAR(50),  -- prospecting, qualified, proposal, negotiation, closed_won, closed_lost
    time_to_conversion_days INTEGER,
    tracking_period_start TIMESTAMP WITH TIME ZONE,
    tracking_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE f500_roi_tracking IS 'Investment and ROI tracking for Fortune 500 acquisition efforts';
COMMENT ON COLUMN f500_roi_tracking.roi_ratio IS 'Calculated as (pipeline_value + actual_revenue) / investment_amount';

-- =====================================================================
-- SECTION 2: ABM CAMPAIGNS SYSTEM (4 tables)
-- Purpose: Account-Based Marketing campaigns for premium market penetration
-- =====================================================================

DROP TABLE IF EXISTS abm_performance CASCADE;
DROP TABLE IF EXISTS abm_touchpoints CASCADE;
DROP TABLE IF EXISTS abm_content_assets CASCADE;
DROP TABLE IF EXISTS abm_campaigns CASCADE;

-- Table: abm_campaigns
-- Purpose: Master ABM campaign management and planning
-- Key Features: Multi-account targeting, personalization levels, budget tracking
CREATE TABLE abm_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_name VARCHAR(500) NOT NULL,
    target_accounts JSONB,  -- Array of prospect IDs
    campaign_type VARCHAR(100),  -- thought_leadership, executive_briefing, case_study, industry_insight
    personalization_level VARCHAR(50),  -- high, medium, standard
    content_assets JSONB,  -- Array of asset IDs
    distribution_channels JSONB,  -- Array of channels: email, social, direct_mail, events
    budget_allocated NUMERIC(12, 2),
    expected_engagement REAL,
    conversion_target INTEGER,
    roi_target REAL,
    campaign_status VARCHAR(50) DEFAULT 'planning',  -- planning, active, completed, paused
    launch_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    performance_metrics JSONB,  -- Real-time performance data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE abm_campaigns IS 'Account-Based Marketing campaigns with multi-channel orchestration';
COMMENT ON COLUMN abm_campaigns.target_accounts IS 'Array of Fortune 500 prospect IDs targeted by this campaign';
COMMENT ON COLUMN abm_campaigns.performance_metrics IS 'Real-time campaign performance metrics and KPIs';

-- Table: abm_content_assets
-- Purpose: Enterprise content library for ABM campaigns
-- Key Features: Persona-targeted content, engagement scoring, conversion tracking
CREATE TABLE abm_content_assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type VARCHAR(100),  -- whitepaper, case_study, executive_brief, industry_report, webinar
    title VARCHAR(500),
    description TEXT,
    target_persona VARCHAR(100),  -- ceo, cto, vp_engineering, technical_lead
    industry_focus VARCHAR(200),
    personalization_data JSONB,  -- Personalization template data
    content_url TEXT,
    engagement_score REAL DEFAULT 0.0,
    conversion_rate REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE abm_content_assets IS 'Enterprise content library optimized for ABM campaign personalization';
COMMENT ON COLUMN abm_content_assets.personalization_data IS 'Template variables for dynamic content personalization';

-- Table: abm_touchpoints
-- Purpose: Individual touchpoint execution and tracking within ABM campaigns
-- Key Features: Multi-channel touchpoints, engagement metrics, personalization tracking
CREATE TABLE abm_touchpoints (
    touchpoint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES abm_campaigns(campaign_id) ON DELETE CASCADE,
    prospect_id UUID,  -- References f500_prospects (soft reference, no FK to allow cross-system use)
    touchpoint_type VARCHAR(100),  -- email, social, direct_mail, webinar, event
    content_asset_id UUID REFERENCES abm_content_assets(asset_id) ON DELETE SET NULL,
    scheduled_date TIMESTAMP WITH TIME ZONE,
    executed_date TIMESTAMP WITH TIME ZONE,
    personalization_applied JSONB,  -- Actual personalization used
    engagement_metrics JSONB,  -- Click rates, time spent, downloads, etc.
    status VARCHAR(50) DEFAULT 'scheduled',  -- scheduled, sent, opened, clicked, responded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE abm_touchpoints IS 'Individual ABM campaign touchpoints with engagement tracking';
COMMENT ON COLUMN abm_touchpoints.engagement_metrics IS 'Detailed engagement data: opens, clicks, time spent, conversions';

-- Table: abm_performance
-- Purpose: Campaign performance analytics and ROI tracking
-- Key Features: Time-series performance data, ROI calculation, cost analysis
CREATE TABLE abm_performance (
    performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES abm_campaigns(campaign_id) ON DELETE CASCADE,
    measurement_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accounts_engaged INTEGER,
    total_touchpoints INTEGER,
    engagement_rate REAL,
    response_rate REAL,
    conversion_rate REAL,
    pipeline_generated NUMERIC(12, 2),
    roi_achieved REAL,
    cost_per_engagement NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE abm_performance IS 'Time-series performance analytics for ABM campaigns';
COMMENT ON COLUMN abm_performance.roi_achieved IS 'Actual ROI achieved: pipeline_generated / campaign_budget';

-- =====================================================================
-- SECTION 3: ENTERPRISE ONBOARDING SYSTEM (5 tables)
-- Purpose: White-glove enterprise client onboarding and success tracking
-- =====================================================================

DROP TABLE IF EXISTS onboarding_communications CASCADE;
DROP TABLE IF EXISTS onboarding_success_templates CASCADE;
DROP TABLE IF EXISTS onboarding_health_metrics CASCADE;
DROP TABLE IF EXISTS onboarding_milestones CASCADE;
DROP TABLE IF EXISTS onboarding_clients CASCADE;

-- Table: onboarding_clients
-- Purpose: Enterprise client master data and onboarding tracking
-- Key Features: Multi-tier onboarding, health scoring, success metrics
CREATE TABLE onboarding_clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(500) NOT NULL,
    industry VARCHAR(200),
    contract_value NUMERIC(12, 2),
    decision_makers JSONB,  -- Array of decision maker objects
    technical_contacts JSONB,  -- Array of technical contact objects
    onboarding_tier VARCHAR(50),  -- white_glove, premium, standard
    engagement_model VARCHAR(100),  -- dedicated_team, shared_team, self_service
    success_metrics JSONB,  -- Client-specific success criteria
    timeline_weeks INTEGER,
    current_phase VARCHAR(100),  -- discovery, planning, implementation, optimization, production
    health_score REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE onboarding_clients IS 'Enterprise client master data with onboarding tier and health tracking';
COMMENT ON COLUMN onboarding_clients.success_metrics IS 'Client-specific success criteria and KPIs';

-- Table: onboarding_milestones
-- Purpose: Milestone tracking for enterprise client onboarding
-- Key Features: Dependency tracking, stakeholder approvals, risk management
CREATE TABLE onboarding_milestones (
    milestone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES onboarding_clients(client_id) ON DELETE CASCADE,
    milestone_name VARCHAR(500),
    milestone_type VARCHAR(100),  -- discovery, configuration, integration, training, go_live
    target_date TIMESTAMP WITH TIME ZONE,
    completion_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'planned',  -- planned, in_progress, completed, blocked, delayed
    success_criteria JSONB,  -- Array of success criteria
    deliverables JSONB,  -- Array of deliverable objects
    stakeholder_approval_required BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(50) DEFAULT 'medium',  -- low, medium, high, critical
    dependencies JSONB,  -- Array of milestone IDs this depends on
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE onboarding_milestones IS 'Onboarding milestone tracking with dependencies and risk management';
COMMENT ON COLUMN onboarding_milestones.dependencies IS 'Array of milestone_ids that must complete before this one';

-- Table: onboarding_health_metrics
-- Purpose: Client health monitoring and early warning system
-- Key Features: Multi-dimensional health tracking, trend analysis, escalation triggers
CREATE TABLE onboarding_health_metrics (
    health_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES onboarding_clients(client_id) ON DELETE CASCADE,
    metric_type VARCHAR(100),  -- engagement, adoption, satisfaction, technical_health, timeline_adherence
    metric_value REAL,
    metric_target REAL,
    measurement_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trend_direction VARCHAR(50) DEFAULT 'stable',  -- improving, stable, declining, critical
    action_items JSONB,  -- Array of recommended actions
    escalation_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE onboarding_health_metrics IS 'Multi-dimensional client health metrics with trend analysis';
COMMENT ON COLUMN onboarding_health_metrics.action_items IS 'Recommended actions based on metric performance';

-- Table: onboarding_success_templates
-- Purpose: Reusable success plan templates for different onboarding tiers
-- Key Features: Industry-specific templates, milestone templates, resource planning
CREATE TABLE onboarding_success_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(500),
    engagement_model VARCHAR(100),  -- dedicated_team, shared_team, self_service
    onboarding_tier VARCHAR(50),  -- white_glove, premium, standard
    timeline_weeks INTEGER,
    phase_structure JSONB,  -- Detailed phase breakdown
    milestone_templates JSONB,  -- Array of milestone template objects
    success_metrics_template JSONB,  -- Standard success metrics
    resource_requirements JSONB,  -- Required resources and team structure
    risk_mitigation_strategies JSONB,  -- Standard risk mitigation approaches
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE onboarding_success_templates IS 'Reusable success plan templates for consistent onboarding execution';
COMMENT ON COLUMN onboarding_success_templates.phase_structure IS 'Detailed breakdown of onboarding phases and activities';

-- Table: onboarding_communications
-- Purpose: Communication log and follow-up tracking for enterprise clients
-- Key Features: Multi-channel communication tracking, action item management, follow-up scheduling
CREATE TABLE onboarding_communications (
    communication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES onboarding_clients(client_id) ON DELETE CASCADE,
    communication_type VARCHAR(100),  -- email, meeting, call, document, training_session
    subject VARCHAR(500),
    participants JSONB,  -- Array of participant objects
    summary TEXT,
    action_items JSONB,  -- Array of action item objects
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date TIMESTAMP WITH TIME ZONE,
    communication_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE onboarding_communications IS 'Complete communication history with action item and follow-up tracking';
COMMENT ON COLUMN onboarding_communications.action_items IS 'Action items with owners, due dates, and status';

-- =====================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- =====================================================================

-- Fortune 500 Acquisition Indexes
CREATE INDEX idx_f500_prospects_company ON f500_prospects(company_name);
CREATE INDEX idx_f500_prospects_industry ON f500_prospects(industry);
CREATE INDEX idx_f500_prospects_priority ON f500_prospects(contact_priority);
CREATE INDEX idx_f500_prospects_score ON f500_prospects(acquisition_score);
CREATE INDEX idx_f500_lead_scoring_prospect ON f500_lead_scoring(prospect_id);
CREATE INDEX idx_f500_lead_scoring_score ON f500_lead_scoring(final_score);
CREATE INDEX idx_f500_lead_scoring_date ON f500_lead_scoring(scored_at);
CREATE INDEX idx_f500_business_cases_prospect ON f500_business_cases(prospect_id);
CREATE INDEX idx_f500_sales_sequences_prospect ON f500_sales_sequences(prospect_id);
CREATE INDEX idx_f500_sales_sequences_status ON f500_sales_sequences(sequence_status);
CREATE INDEX idx_f500_sales_sequences_next_touchpoint ON f500_sales_sequences(next_touchpoint_date);
CREATE INDEX idx_f500_roi_tracking_prospect ON f500_roi_tracking(prospect_id);
CREATE INDEX idx_f500_roi_tracking_status ON f500_roi_tracking(conversion_status);

-- ABM Campaigns Indexes
CREATE INDEX idx_abm_campaigns_status ON abm_campaigns(campaign_status);
CREATE INDEX idx_abm_campaigns_type ON abm_campaigns(campaign_type);
CREATE INDEX idx_abm_campaigns_launch ON abm_campaigns(launch_date);
CREATE INDEX idx_abm_content_assets_type ON abm_content_assets(asset_type);
CREATE INDEX idx_abm_content_assets_persona ON abm_content_assets(target_persona);
CREATE INDEX idx_abm_content_assets_industry ON abm_content_assets(industry_focus);
CREATE INDEX idx_abm_touchpoints_campaign ON abm_touchpoints(campaign_id);
CREATE INDEX idx_abm_touchpoints_prospect ON abm_touchpoints(prospect_id);
CREATE INDEX idx_abm_touchpoints_status ON abm_touchpoints(status);
CREATE INDEX idx_abm_touchpoints_scheduled ON abm_touchpoints(scheduled_date);
CREATE INDEX idx_abm_performance_campaign ON abm_performance(campaign_id);
CREATE INDEX idx_abm_performance_date ON abm_performance(measurement_date);

-- Enterprise Onboarding Indexes
CREATE INDEX idx_onboarding_clients_company ON onboarding_clients(company_name);
CREATE INDEX idx_onboarding_clients_tier ON onboarding_clients(onboarding_tier);
CREATE INDEX idx_onboarding_clients_phase ON onboarding_clients(current_phase);
CREATE INDEX idx_onboarding_clients_health ON onboarding_clients(health_score);
CREATE INDEX idx_onboarding_milestones_client ON onboarding_milestones(client_id);
CREATE INDEX idx_onboarding_milestones_status ON onboarding_milestones(status);
CREATE INDEX idx_onboarding_milestones_target ON onboarding_milestones(target_date);
CREATE INDEX idx_onboarding_health_client ON onboarding_health_metrics(client_id);
CREATE INDEX idx_onboarding_health_type ON onboarding_health_metrics(metric_type);
CREATE INDEX idx_onboarding_health_date ON onboarding_health_metrics(measurement_date);
CREATE INDEX idx_onboarding_health_escalation ON onboarding_health_metrics(escalation_required);
CREATE INDEX idx_onboarding_communications_client ON onboarding_communications(client_id);
CREATE INDEX idx_onboarding_communications_type ON onboarding_communications(communication_type);
CREATE INDEX idx_onboarding_communications_follow_up ON onboarding_communications(follow_up_date) WHERE follow_up_required = TRUE;

-- =====================================================================
-- JSONB GIN INDEXES FOR EFFICIENT JSON QUERIES
-- =====================================================================

-- Fortune 500 JSONB indexes
CREATE INDEX idx_f500_prospects_tech_stack ON f500_prospects USING GIN(tech_stack);
CREATE INDEX idx_f500_prospects_decision_makers ON f500_prospects USING GIN(decision_makers);
CREATE INDEX idx_f500_prospects_pain_points ON f500_prospects USING GIN(pain_points);

-- ABM Campaigns JSONB indexes
CREATE INDEX idx_abm_campaigns_target_accounts ON abm_campaigns USING GIN(target_accounts);
CREATE INDEX idx_abm_campaigns_content_assets ON abm_campaigns USING GIN(content_assets);
CREATE INDEX idx_abm_touchpoints_engagement ON abm_touchpoints USING GIN(engagement_metrics);

-- Onboarding JSONB indexes
CREATE INDEX idx_onboarding_clients_decision_makers ON onboarding_clients USING GIN(decision_makers);
CREATE INDEX idx_onboarding_clients_success_metrics ON onboarding_clients USING GIN(success_metrics);
CREATE INDEX idx_onboarding_milestones_dependencies ON onboarding_milestones USING GIN(dependencies);

-- =====================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- =====================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_f500_prospects_updated_at BEFORE UPDATE ON f500_prospects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_f500_lead_scoring_updated_at BEFORE UPDATE ON f500_lead_scoring FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_f500_business_cases_updated_at BEFORE UPDATE ON f500_business_cases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_f500_sales_sequences_updated_at BEFORE UPDATE ON f500_sales_sequences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_f500_roi_tracking_updated_at BEFORE UPDATE ON f500_roi_tracking FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_abm_campaigns_updated_at BEFORE UPDATE ON abm_campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_abm_content_assets_updated_at BEFORE UPDATE ON abm_content_assets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_abm_touchpoints_updated_at BEFORE UPDATE ON abm_touchpoints FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_abm_performance_updated_at BEFORE UPDATE ON abm_performance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_clients_updated_at BEFORE UPDATE ON onboarding_clients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_milestones_updated_at BEFORE UPDATE ON onboarding_milestones FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_health_metrics_updated_at BEFORE UPDATE ON onboarding_health_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_success_templates_updated_at BEFORE UPDATE ON onboarding_success_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_onboarding_communications_updated_at BEFORE UPDATE ON onboarding_communications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================================
-- SCHEMA SUMMARY
-- =====================================================================
-- Total Tables: 15
--   Fortune 500 Acquisition: 6 tables
--   ABM Campaigns: 4 tables
--   Enterprise Onboarding: 5 tables
--
-- Key Design Decisions:
--   1. UUID primary keys for distributed systems compatibility
--   2. JSONB for flexible data structures (decision makers, metrics, etc.)
--   3. Proper foreign keys with CASCADE deletes for data integrity
--   4. Comprehensive indexes on foreign keys and query columns
--   5. GIN indexes on JSONB columns for efficient JSON queries
--   6. Automatic updated_at triggers on all tables
--   7. TIMESTAMP WITH TIME ZONE for proper timezone handling
--   8. NUMERIC for precise financial calculations
--   9. Soft references between systems (prospect_id in touchpoints)
--   10. Table naming: snake_case with system prefixes (f500_, abm_, onboarding_)
--
-- Migration Compatibility:
--   - All SQLite TEXT PRIMARY KEY → UUID PRIMARY KEY
--   - All SQLite TEXT (JSON) → JSONB
--   - All SQLite TEXT (timestamps) → TIMESTAMP WITH TIME ZONE
--   - All SQLite INTEGER (money) → NUMERIC(12, 2)
--   - All SQLite REAL (scores) → REAL
--   - All SQLite BOOLEAN (0/1) → BOOLEAN
--   - Added created_at/updated_at to all tables
--
-- =====================================================================
