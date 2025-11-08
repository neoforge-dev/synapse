# Epic 19: Router Consolidation Map

## Target Architecture (5 files only)

**KEEP THESE FILES:**
1. `__init__.py` - Package initialization
2. `core_business_operations.py` - Documents, ingestion, search, query, Epic 7 CRM
3. `enterprise_platform.py` - Auth, admin, compliance, monitoring
4. `analytics_intelligence.py` - Dashboard, analytics, audience, concepts
5. `advanced_features.py` - Graph, reasoning, specialized features

**SPECIAL CASE:**
- `unified_business_intelligence_api.py` - Currently imported in main.py (line 37), will evaluate for removal

## Legacy Router Mapping (36 files to DELETE)

### Batch 1: Clearly Unused (Low Risk)
- `concepts_original.py` - Old backup, superseded by concepts.py → analytics_intelligence.py
- `chunks.py` - Unused chunk router, functionality in core_business_operations.py
- `core_business.py` - Old version, superseded by core_business_operations.py

### Batch 2: Document Management (Consolidated → core_business_operations.py)
- `documents.py` - Document CRUD → core_business_operations.py
- `ingestion.py` - Document ingestion → core_business_operations.py
- `search.py` - Search functionality → core_business_operations.py
- `query.py` - Query functionality → core_business_operations.py

### Batch 3: Authentication & Admin (Consolidated → enterprise_platform.py)
- `auth.py` - Basic auth → enterprise_platform.py
- `enterprise_auth.py` - Enterprise auth → enterprise_platform.py
- `admin.py` - Admin functionality → enterprise_platform.py
- `administration.py` - Duplicate admin → enterprise_platform.py
- `monitoring.py` - Monitoring → enterprise_platform.py
- `compliance.py` - Compliance → enterprise_platform.py

### Batch 4: Analytics (Consolidated → analytics_intelligence.py)
- `dashboard.py` - Dashboard → analytics_intelligence.py
- `analytics.py` - Analytics → analytics_intelligence.py
- `audience.py` - Audience analysis → analytics_intelligence.py
- `concepts.py` - Concept analysis → analytics_intelligence.py
- `content_strategy.py` - Content strategy → analytics_intelligence.py

### Batch 5: Advanced Features (Consolidated → advanced_features.py)
- `graph.py` - Graph operations → advanced_features.py
- `reasoning.py` - Reasoning → advanced_features.py
- `hot_takes.py` - Hot takes → advanced_features.py
- `brand_safety.py` - Brand safety → advanced_features.py

### Batch 6: Unified Routers (Epic 2, functionality in consolidated routers)
- `unified_content.py` - Consolidated into core_business_operations.py
- `unified_content_simple.py` - Consolidated into core_business_operations.py
- `unified_retrieval.py` - Consolidated into core_business_operations.py
- `unified_business_intelligence.py` - Consolidated into analytics_intelligence.py
- `unified_business_intelligence_api.py` - SPECIAL: Currently imported in main.py, evaluate removal
- `unified_graph_operations.py` - Consolidated into advanced_features.py
- `unified_platform.py` - Consolidated into enterprise_platform.py
- `unified_specialized_features.py` - Consolidated into advanced_features.py
- `unified_system_admin.py` - Consolidated into enterprise_platform.py

### Batch 7: Epic-Specific (Business Value Routers - Review Carefully)
- `epic7_sales_automation.py` - Sales automation ($1.158M value) - CHECK IF USED
- `epic16_enterprise_acquisition.py` - Enterprise acquisition - CHECK IF USED
- `epic18_global_partnerships.py` - Global partnerships - CHECK IF USED
- `autonomous_ai_demo.py` - Demo router - CHECK IF USED

## Deletion Strategy

1. **Verify imports**: Ensure only main.py imports routers
2. **Batch deletions**: Execute in order, commit after each batch
3. **Test between batches**: Quick smoke test to ensure no breakage
4. **Special handling**: Epic-specific routers need business impact assessment
5. **Final validation**: Exactly 5 files remain (or 4 if unified_business_intelligence_api removed)

## Success Criteria

- ✅ Git tag backup created: `pre-router-cleanup-20251005`
- ⏳ 36+ legacy files removed
- ⏳ Only 4-5 router files remain
- ⏳ Zero import errors
- ⏳ All functionality preserved in consolidated routers
- ⏳ Documentation updated
