# TechLead AutoPilot Handoff Prompt

**Context**: You are taking over a sophisticated SaaS platform development project that has strong foundations and needs focused execution to reach €10K MRR.

## 📋 **Project Status & Handoff**

### **What You're Inheriting**
You're joining the **TechLead AutoPilot** project - an enterprise-grade SaaS platform for technical leadership automation. This platform has already proven the business model by generating **€290K in consultation pipeline value** through AI-powered LinkedIn content generation and lead detection.

### **Current State (January 2024)**
- **Backend**: 85% complete with FastAPI, multi-tenant architecture, enterprise security
- **Frontend**: 60% complete with Next.js 14, TypeScript, PWA capabilities  
- **Business Logic**: Core algorithms implemented and proven (€290K results)
- **Infrastructure**: Production-ready with comprehensive documentation
- **Technical Debt**: Recently resolved - all systems clean and modern

### **Your Mission**
Implement **Epic 1: LinkedIn Automation & Scheduling Engine** to unlock the core value proposition that generated the €290K consultation pipeline. This is the highest business impact work that directly enables customer value.

---

## 🎯 **Epic 1: LinkedIn Automation & Scheduling Engine**

**Duration**: 3 weeks | **Business Impact**: CRITICAL | **Priority**: #1

### **Epic Goal**
Enable automated LinkedIn content posting with proven engagement optimization so technical consultants can systematically generate consultation inquiries without manual effort.

### **Success Definition**  
After Epic 1, users should be able to:
1. Connect their LinkedIn account via OAuth
2. Schedule AI-generated content for optimal posting times (6:30 AM Tue/Thu)
3. Have content automatically posted to LinkedIn
4. See real-time engagement metrics synced from LinkedIn
5. Approve content via mobile-responsive interface

---

## 🗺️ **Implementation Roadmap**

### **Week 1: LinkedIn OAuth & Background Jobs**
**Focus**: Enable LinkedIn account connection and job processing infrastructure

#### **Key Deliverables**
1. **Complete LinkedIn OAuth 2.0 implementation**
   - File: `src/techlead_autopilot/services/linkedin_service.py` 
   - Implement full OAuth flow with required scopes: `w_member_social`, `r_liteprofile`, `r_emailaddress`
   - Handle token storage in encrypted database fields
   - Implement token refresh with error handling

2. **Background job system (Celery + Redis)**
   - File: `src/techlead_autopilot/infrastructure/jobs/` (create directory)
   - Set up Celery with Redis broker for async task processing
   - Create job monitoring and health check endpoints
   - Implement job retry logic and error handling

3. **LinkedIn API client with rate limiting**
   - File: `src/techlead_autopilot/services/external_apis/linkedin_client.py`
   - Implement exponential backoff and rate limit respect
   - Add comprehensive error handling and logging
   - Create connection health monitoring

#### **Testing Requirements**
- OAuth flow works end-to-end (mock LinkedIn for tests)
- Background jobs process successfully with monitoring
- Rate limiting prevents API violations
- Error handling gracefully manages failures

### **Week 2: Automated Posting Engine**
**Focus**: Core posting functionality with optimal timing

#### **Key Deliverables**
1. **Content posting service**
   - File: `src/techlead_autopilot/services/posting_service.py`
   - Integrate with LinkedIn API for content publishing
   - Handle content formatting and hashtag optimization
   - Implement posting confirmation and status tracking

2. **Scheduling engine with optimal timing**
   - File: `src/techlead_autopilot/services/scheduler_service.py`
   - Implement 6:30 AM Tue/Thu optimal posting algorithm
   - Support multiple time zones for global users
   - Create scheduling queue management

3. **Error handling and retry mechanism**
   - Implement comprehensive error classification
   - Create retry policies for different failure types
   - Add monitoring and alerting for posting failures
   - Ensure posting reliability >99%

#### **Testing Requirements**
- Content posts successfully to LinkedIn (with test account)
- Scheduling respects optimal timing algorithms
- Retry mechanism handles various failure scenarios
- Monitoring alerts on posting issues

### **Week 3: Engagement Analytics & Mobile Approval**
**Focus**: Complete the feedback loop with analytics and mobile experience

#### **Key Deliverables**
1. **LinkedIn Analytics API integration**
   - File: `src/techlead_autopilot/services/analytics_service.py`
   - Sync engagement metrics (likes, comments, shares, impressions)
   - Real-time data collection and storage
   - Performance trending and analysis

2. **Mobile-responsive content approval workflow**
   - Files: `frontend/src/app/approval/` (create mobile-optimized pages)
   - Implement PWA-compatible approval interface
   - Add offline capabilities for content review
   - Create push notifications for approval requests

3. **Engagement prediction validation**
   - Validate accuracy against proven €290K templates
   - Implement feedback loop for prediction improvement
   - Create performance dashboards

#### **Testing Requirements**
- Analytics sync accurately from LinkedIn
- Mobile approval workflow functions offline
- Engagement predictions maintain 85%+ accuracy
- Dashboard displays real-time performance data

---

## 🛠️ **Technical Architecture Guide**

### **Key System Components**
```
LinkedIn OAuth → Content Scheduler → Background Jobs → Analytics Sync
     ↓                ↓                    ↓               ↓
Token Management → Posting Engine → Job Queue → Metrics Collection
```

### **Database Schema Extensions**
- **linkedin_integrations** table already exists - use existing structure
- **background_jobs** table - create for job tracking
- **posting_schedule** table - create for scheduling management
- **engagement_metrics** table - extend content_generated table

### **API Endpoints to Implement**
- `POST /api/v1/integrations/linkedin/connect` - Initiate OAuth
- `GET /api/v1/integrations/linkedin/callback` - Handle OAuth callback  
- `POST /api/v1/content/{id}/schedule` - Schedule content posting
- `GET /api/v1/content/{id}/analytics` - Get engagement metrics
- `POST /api/v1/content/{id}/approve` - Mobile content approval

### **Configuration Requirements**
- LinkedIn OAuth credentials in environment variables
- Celery broker configuration (Redis)
- Job monitoring and alerting setup
- Mobile PWA service worker configuration

---

## 📚 **Key Files & Locations**

### **Backend Implementation**
- **LinkedIn Service**: `src/techlead_autopilot/services/linkedin_service.py`
- **Posting Service**: `src/techlead_autopilot/services/posting_service.py`
- **Background Jobs**: `src/techlead_autopilot/infrastructure/jobs/`
- **API Router**: `src/techlead_autopilot/api/routers/integrations.py` (create)
- **Database Models**: `src/techlead_autopilot/infrastructure/database/models.py` (extend)

### **Frontend Implementation**
- **OAuth Pages**: `frontend/src/app/integrations/linkedin/`
- **Approval Interface**: `frontend/src/app/approval/`
- **Analytics Dashboard**: `frontend/src/app/analytics/`
- **Mobile PWA**: `frontend/src/components/mobile/`

### **Configuration Files**
- **Environment**: `.env` (add LinkedIn OAuth credentials)
- **Celery Config**: `src/techlead_autopilot/infrastructure/jobs/celery_config.py`
- **LinkedIn Client**: `src/techlead_autopilot/services/external_apis/linkedin_client.py`

### **Testing**
- **Integration Tests**: `tests/integration/test_linkedin_integration.py`
- **Service Tests**: `tests/services/test_posting_service.py`
- **API Tests**: `tests/api/test_integrations.py`

---

## 🧪 **Testing Strategy**

### **Test-Driven Development Approach**
1. **Write failing tests** that define expected behavior
2. **Implement minimal code** to pass tests  
3. **Refactor** while keeping tests green
4. **Maintain >85% coverage** for critical paths

### **Key Test Categories**
- **OAuth Flow Tests**: Mock LinkedIn OAuth and verify token handling
- **Posting Tests**: Test content publishing with LinkedIn API mocks
- **Scheduling Tests**: Verify optimal timing algorithms and queue management
- **Error Handling Tests**: Validate retry logic and failure recovery
- **Mobile Tests**: PWA functionality and offline capabilities

### **Test Data Requirements**
- Mock LinkedIn OAuth responses
- Sample content generation data
- Test LinkedIn API responses
- Mobile device simulation scenarios

---

## 💡 **First Principles Approach**

### **Fundamental Business Truth**
Technical consultants generated €290K in consultation pipeline by consistently posting optimized LinkedIn content at proven times (6:30 AM Tue/Thu) with high-quality, engagement-focused content.

### **Essential User Journey**
User Connects LinkedIn → Content Generated → Content Scheduled → Posted Automatically → Engagement Tracked → Leads Detected

### **Critical Success Factors**
1. **Reliability**: 99%+ posting success rate - failures lose business opportunities
2. **Timing**: Exact 6:30 AM Tue/Thu posting - timing drives engagement
3. **Quality**: Content maintains proven templates - quality drives lead generation
4. **Automation**: Zero manual intervention - automation enables scalability

### **Technical Constraints**
- LinkedIn API rate limits (300 posts/day, 500 API requests/day)
- OAuth token expiration (60 days, requires refresh)
- Time zone complexity for global users
- Mobile network reliability for approval workflow

---

## 🚀 **Getting Started Instructions**

### **1. Environment Setup**
```bash
# Ensure you have the development environment ready
uv run pytest tests/test_simple.py -v  # Verify 8/8 tests passing

# Check current LinkedIn integration status
grep -r "linkedin" src/techlead_autopilot/services/
```

### **2. Review Existing Code**
**Priority Files to Read**:
1. `src/techlead_autopilot/infrastructure/database/models.py` - Study LinkedInIntegration model
2. `src/techlead_autopilot/services/` - Review existing service patterns
3. `docs/PLAN.md` - Full context and epic definitions  
4. `frontend/src/app/` - Understand existing frontend patterns

### **3. Create Development Branch**
```bash
git checkout -b epic-1-linkedin-automation
git push -u origin epic-1-linkedin-automation
```

### **4. Start with Tests**
```bash
# Create the first failing test
touch tests/integration/test_linkedin_integration.py
# Write test for OAuth flow
# Then implement the OAuth service to make it pass
```

### **5. Daily Progress Tracking**
- Update todo list with completed items
- Commit frequently with descriptive messages
- Run full test suite before each commit
- Update Epic 1 checklist in docs/PLAN.md

---

## 📊 **Success Metrics & Validation**

### **Week 1 Success Criteria**
- [ ] LinkedIn OAuth flow works end-to-end
- [ ] Background job system processes tasks reliably
- [ ] API rate limiting prevents violations
- [ ] OAuth tokens refresh automatically
- [ ] Health checks report system status

### **Week 2 Success Criteria**  
- [ ] Content posts successfully to LinkedIn
- [ ] Scheduling respects 6:30 AM Tue/Thu timing
- [ ] Error handling achieves >99% reliability
- [ ] Retry mechanism handles all failure types
- [ ] Posting status tracked accurately

### **Week 3 Success Criteria**
- [ ] Engagement metrics sync from LinkedIn
- [ ] Mobile approval interface works offline
- [ ] Analytics dashboard shows real-time data  
- [ ] Engagement predictions maintain accuracy
- [ ] Push notifications deliver to mobile devices

### **Epic 1 Completion Definition**
✅ **Complete when**: A user can connect LinkedIn, generate content, schedule it for optimal times, have it posted automatically, and see real-time engagement metrics - all while approving content via mobile interface.

---

## 🔄 **Handoff & Communication**

### **When You Need Help**
- **Technical Questions**: Check existing patterns in the codebase first
- **Business Logic**: Refer to the €290K proven algorithms in the business logic
- **Architecture Decisions**: Follow existing patterns in services and infrastructure
- **Priority Questions**: Epic 1 is the highest priority - focus there exclusively

### **Progress Reporting**
- **Daily**: Update todo list and commit progress
- **Weekly**: Update Epic 1 checklist in docs/PLAN.md
- **Blockers**: Document in todo list with "blocked" status and context

### **Quality Standards**
- **Test Coverage**: Maintain >85% coverage for new code
- **Code Style**: Follow existing patterns in the codebase
- **Security**: Review all OAuth and token handling carefully
- **Performance**: API endpoints must respond in <200ms

### **Next Epic Preparation**
After Epic 1 completion, you'll continue with Epic 3 (Revenue & Customer Success Engine) to enable billing and customer onboarding. The foundation you build in Epic 1 will be crucial for business success.

---

## 🎯 **Final Thoughts**

You're working on a proven business model with solid technical foundations. The €290K consultation pipeline validates that this approach works. Your job is to implement the LinkedIn automation that enables this value for customers.

**Focus on**:
- **Business impact over technical perfection** - get the core user journey working
- **Reliability over features** - 99% posting reliability is more valuable than advanced scheduling options
- **User experience over technical elegance** - the mobile approval workflow determines user adoption
- **Test-driven implementation** - comprehensive tests ensure production reliability

**Remember**: This isn't a greenfield project. You have proven algorithms, established patterns, and clear business validation. Follow the existing architecture, maintain the quality standards, and focus on delivering Epic 1 completely.

**Start here**: Read docs/PLAN.md for full context, then implement LinkedIn OAuth as your first milestone.

---

**Handoff Complete** ✅  
**Next Action**: Implement LinkedIn OAuth 2.0 flow  
**Success Target**: Epic 1 complete in 3 weeks  
**Business Impact**: Unlock €290K proven consultation pipeline for customers