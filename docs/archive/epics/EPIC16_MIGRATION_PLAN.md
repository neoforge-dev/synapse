# Epic 16 PostgreSQL Migration Plan

**Epic 20 Phase 4: Fortune 500 Acquisition System**
**Last Updated:** 2025-10-08
**Status:** Planning Complete | Ready for Implementation
**Estimated Effort:** 212 hours (6 weeks with buffer)

---

## Executive Summary

Epic 16 consists of 3 integrated systems managing the Fortune 500 enterprise acquisition pipeline:
- **Fortune 500 Acquisition** ($5M+ ARR potential): 50-100 prospects, AI-powered scoring
- **ABM Campaigns**: 100-200 touchpoints, multi-channel engagement
- **Enterprise Onboarding**: 30-50 clients, success tracking

### Migration Scope
- **Databases**: 3 SQLite → 1 PostgreSQL (`synapse_business_core`)
- **Tables**: 15 tables (6 + 4 + 5)
- **Code Files**: 3 files, 3,760 lines, 20 sqlite3 calls
- **Service Layer**: 3 new services, 141 methods, 2,600 lines
- **Tests**: 150+ unit tests, 30+ integration tests

---

## Database Architecture

### Current State (SQLite)
```
epic16_fortune500_acquisition.db   → 6 tables  → 50-100 rows
epic16_abm_campaigns.db            → 4 tables  → 100-200 rows
epic16_enterprise_onboarding.db    → 5 tables  → 30-50 rows
```

### Target State (PostgreSQL)
```
synapse_business_core (PostgreSQL)
├── f500_prospects              (Fortune 500 companies)
├── f500_lead_scoring           (AI scoring history)
├── f500_business_cases         (ROI calculations)
├── f500_sales_sequences        (Multi-touch engagement)
├── f500_roi_tracking           (Investment tracking)
├── abm_campaigns               (ABM campaigns)
├── abm_content_assets          (Content library)
├── abm_touchpoints             (Touchpoint tracking)
├── abm_performance             (Performance metrics)
├── onboarding_clients          (Enterprise clients)
├── onboarding_milestones       (Milestone tracking)
├── onboarding_health_metrics   (Health monitoring)
├── onboarding_success_templates (Success plans)
└── onboarding_communications   (Communication log)
```

---

## Service Layer Architecture

### New Services (3)

#### 1. Epic16Service (Fortune 500 Acquisition)
- **Methods**: 49 (prospect management, scoring, business cases, sequences, ROI)
- **Lines**: ~900
- **Database**: `synapse_business_core` (schema prefix: `f500_`)
- **Integration**: Epic 7 CRM (prospect → contact conversion)

#### 2. Epic16ABMService (ABM Campaigns)
- **Methods**: 38 (campaigns, content assets, touchpoints, performance)
- **Lines**: ~700
- **Database**: `synapse_business_core` (schema prefix: `abm_`)

#### 3. Epic16OnboardingService (Enterprise Onboarding)
- **Methods**: 44 (clients, milestones, health metrics, success plans)
- **Lines**: ~800
- **Database**: `synapse_business_core` (schema prefix: `onboarding_`)

**Total Service Layer**: 141 methods, 2,600 lines, 150+ tests

---

## Epic 7 Integration (Critical)

### Data Flow
```
Fortune 500 Prospect → Business Case → Sales Sequence → CONVERSION → CRM Contact
(Epic 16 Service)                                                    (Epic 7 CRM)
```

### Integration Points
1. **Prospect → Contact Conversion**
   - Method: `Epic16Service.convert_to_crm_contact(prospect_id)`
   - Triggers: Qualified status + business case accepted
   - Creates CRM contact with full prospect data

2. **Pipeline Protection**
   - Current: fortune500_acquisition.py line 1391 reads Epic 7 SQLite
   - Target: Update to use CRMService instead of direct database access
   - Validation: Ensure $1.158M Epic 7 pipeline protected

3. **Shared Decision Makers**
   - Epic 16: JSON array of decision makers per prospect
   - Epic 7: Individual contact records
   - Strategy: Create multiple CRM contacts from single prospect

---

## 6-Week Implementation Plan

### Week 1: Schema Design & Data Migration
- Create PostgreSQL schema (15 tables)
- Build migration scripts with validation
- Migrate 180-350 rows from 3 SQLite databases
- Validate data integrity (100% parity)

**Deliverables:**
- `database_migration/epic16_postgresql_migration.py`
- `database_migration/epic16_schema.sql`
- `database_migration/epic16_validation.py`
- Migration validation report

### Week 2: Dual-Write Implementation
- Add PostgreSQL writes to all 3 Epic 16 files
- Implement validation mode (compare SQLite vs PostgreSQL)
- Run dual-write for 24 hours with monitoring
- Fix any data discrepancies

**Deliverables:**
- Updated Epic 16 files with dual-write support
- Validation mode implementation
- 24-hour validation report

### Week 3-4: Service Layer Development
- Create `Epic16Service` (49 methods, 900 lines)
- Create `Epic16ABMService` (38 methods, 700 lines)
- Create `Epic16OnboardingService` (44 methods, 800 lines)
- Create `graph_rag/infrastructure/persistence/models/epic16.py`
- Write 150+ unit tests

**Deliverables:**
- 3 service layer modules (2,600 lines total)
- SQLAlchemy model definitions
- Comprehensive test suites (150+ tests)
- Integration tests with Epic 7 CRM

### Week 5: Code Migration
- Update `epic16_fortune500_acquisition.py` (7 sqlite3 calls → Epic16Service)
- Update `epic16_abm_campaigns.py` (6 sqlite3 calls → Epic16ABMService)
- Update `epic16_enterprise_onboarding.py` (7 sqlite3 calls → Epic16OnboardingService)
- Update `automation_dashboard.py` integration
- Test PostgreSQL-only mode

**Deliverables:**
- Fully migrated Epic 16 codebase
- Updated integration points
- Regression test suite results

### Week 6: Cutover & Validation
- Final data sync from SQLite
- Enable PostgreSQL-only mode
- Monitor for 24-48 hours:
  - Query latency (<50ms target)
  - Error rates (0% target)
  - Business metric accuracy
- Archive SQLite databases (30-day retention)
- Document migration results

**Deliverables:**
- Production cutover completion
- Monitoring dashboard
- Post-migration validation report
- Lessons learned document

---

## Complexity Assessment

### High Complexity (Fortune 500 Acquisition)
- **Lines**: 1,740
- **SQLite Calls**: 7
- **Factors**:
  - Epic 7 CRM integration (line 1391)
  - AI-powered scoring algorithms
  - Complex JSON structures (decision_makers, tech_stack, pain_points)
  - Pipeline value protection requirements
- **Effort**: 16 hours code + 24 hours service = 40 hours

### Medium Complexity (ABM Campaigns)
- **Lines**: 1,080
- **SQLite Calls**: 6
- **Factors**:
  - Content asset library (10+ pre-built assets)
  - Multi-touch campaign sequencing
  - Performance analytics
- **Effort**: 12 hours code + 18 hours service = 30 hours

### Medium Complexity (Enterprise Onboarding)
- **Lines**: 940
- **SQLite Calls**: 7
- **Factors**:
  - Success plan templates (3 templates)
  - Health metric calculations
  - Milestone dependency tracking
- **Effort**: 12 hours code + 20 hours service = 32 hours

**Total Effort**: 184 hours base + 28 hours buffer = **212 hours (6 weeks)**

---

## Risk Assessment

### P0 Critical Risks

**1. Epic 7 Integration Breakage**
- **Risk**: Pipeline protection validation fails
- **Impact**: $1.158M pipeline disruption
- **Mitigation**: Update to use CRMService, comprehensive integration tests
- **Rollback Trigger**: Any Epic 7 pipeline value discrepancy

**2. Fortune 500 Prospect Data Loss**
- **Risk**: Complex JSON data corruption
- **Impact**: Loss of $5M+ ARR acquisition pipeline
- **Mitigation**: Row-level validation, JSON structure checks, 30-day backups
- **Rollback Trigger**: Any data loss detected

**3. Business Logic Regression**
- **Risk**: AI scoring/ROI calculations change
- **Impact**: Incorrect prospect prioritization
- **Mitigation**: Unit tests for all calculations, regression test suite
- **Rollback Trigger**: >5% variance in calculated values

### P1 High Risks

**4. ABM Campaign Performance Tracking**
- **Risk**: Touchpoint scheduling disrupted
- **Impact**: Campaign performance data loss
- **Mitigation**: Dual-write validation, extensive testing

**5. Enterprise Client Onboarding Disruption**
- **Risk**: Health metrics calculation fails
- **Impact**: Missed client escalations
- **Mitigation**: Validate calculations, test milestone logic

---

## Success Criteria

### Technical Metrics
- ✅ 100% data integrity (all 180-350 rows migrated)
- ✅ 0 minutes downtime
- ✅ <50ms query latency
- ✅ 150+ tests passing
- ✅ 0 rollbacks required

### Business Metrics
- ✅ Fortune 500 pipeline protected (all prospects intact)
- ✅ ABM campaigns operational (all touchpoints functioning)
- ✅ Enterprise clients tracked (all onboarding data preserved)
- ✅ Epic 7 integration maintained ($1.158M pipeline)
- ✅ $0 revenue impact

---

## Rollback Procedures

### Rollback Triggers
1. Data loss (missing rows in PostgreSQL)
2. Calculation errors (>5% variance)
3. Epic 7 integration break
4. Performance degradation (>200ms latency)
5. Business disruption (>5 minutes downtime)

### Rollback Steps
1. Disable PostgreSQL mode (`EPIC16_POSTGRESQL_ONLY=false`)
2. Revert code changes (git restore)
3. Restore SQLite databases (from backups)
4. Validate restoration
5. Resume operations
6. Document root cause

---

## Dependencies

### Prerequisites
- ✅ Epic 7 PostgreSQL migration complete (Phase 3)
- ✅ CRM service layer operational
- ✅ PostgreSQL database configured (`synapse_business_core`)
- ⏳ Epic 16 SQLite databases accessible

### Files to Create
- `database_migration/epic16_postgresql_migration.py`
- `database_migration/epic16_schema.sql`
- `database_migration/epic16_validation.py`
- `graph_rag/services/epic16_service.py`
- `graph_rag/services/epic16_abm_service.py`
- `graph_rag/services/epic16_onboarding_service.py`
- `graph_rag/infrastructure/persistence/models/epic16.py`

### Files to Modify
- `business_development/epic16_fortune500_acquisition.py` (7 locations)
- `business_development/epic16_abm_campaigns.py` (6 locations)
- `business_development/epic16_enterprise_onboarding.py` (7 locations)
- `business_development/automation_dashboard.py`

---

## Next Immediate Actions

### Week 1 (Start Immediately)
1. Create PostgreSQL schema script (15 tables)
2. Build migration validator tool
3. Test migration on 10-20 row subset
4. Get stakeholder approval
5. Schedule migration window

### Files to Start With
1. `database_migration/epic16_schema.sql` - Define PostgreSQL tables
2. `graph_rag/infrastructure/persistence/models/epic16.py` - SQLAlchemy models
3. `graph_rag/services/epic16_service.py` - Start with Fortune 500 service

---

**Migration Readiness**: ✅ Plan Complete | Ready for Implementation
**Business Value**: $5M+ ARR Fortune 500 acquisition pipeline
**Risk Level**: Medium (with comprehensive mitigation)
**Approval Required**: Yes (stakeholder sign-off before Week 1)
