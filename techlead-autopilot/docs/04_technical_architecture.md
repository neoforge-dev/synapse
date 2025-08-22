# 04. Technical Architecture
## TechLead AutoPilot - MVP System Design

### **Architecture Principles**
- **Multi-Tenant First**: Designed for thousands of customers from day 1
- **API-Driven**: Clean separation between frontend and backend
- **Horizontal Scaling**: Can grow with customer base
- **Security by Design**: Customer data isolation and protection
- **Cost Optimization**: Efficient resource usage for profitability

### **System Overview**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   API Backend    │    │   External APIs │
│   (React/Next)  │───▶│  (Node.js/FastAPI) │───▶│   (LinkedIn)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Job Queue     │    │   Database       │    │   File Storage  │
│   (Redis/Bull)  │    │   (PostgreSQL)   │    │   (S3/CDN)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Frontend Architecture**

#### **Technology Stack**
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript for type safety
- **Styling**: Tailwind CSS for rapid development
- **State Management**: Zustand or React Query
- **Authentication**: NextAuth.js with JWT tokens

#### **Key Components**
```
src/
├── components/
│   ├── auth/           # Login, signup, profile
│   ├── content/        # Content creation and management
│   ├── analytics/      # Performance dashboards
│   └── leads/          # Lead management interface
├── pages/
│   ├── dashboard/      # Main application dashboard
│   ├── content/        # Content management pages
│   └── settings/       # Account and integration settings
└── lib/
    ├── api/            # API client functions
    ├── auth/           # Authentication utilities
    └── utils/          # Shared utilities
```

#### **Responsive Design**
- **Desktop First**: Optimized for content creation workflow
- **Mobile Responsive**: Essential for lead notification and approval
- **Progressive Web App**: Offline capabilities for mobile users

### **Backend Architecture**

#### **Technology Stack**
- **Framework**: FastAPI (Python) or Express.js (Node.js)
- **Language**: Python 3.11+ or Node.js 18+
- **Database**: PostgreSQL 15+ with connection pooling
- **Cache**: Redis for sessions and job queues
- **Queue System**: Celery (Python) or Bull (Node.js)

#### **Service Architecture**
```
├── api/
│   ├── auth/           # User authentication and authorization
│   ├── content/        # Content generation and management
│   ├── linkedin/       # LinkedIn API integration
│   ├── leads/          # Lead detection and scoring
│   └── analytics/      # Performance tracking
├── services/
│   ├── content_engine/ # Core content generation logic
│   ├── nlp_processor/  # Natural language processing
│   ├── scheduler/      # Content posting scheduling
│   └── notification/   # Alert and notification system
└── models/
    ├── user.py         # User and account models
    ├── content.py      # Content and posting models
    └── leads.py        # Lead and inquiry models
```

### **Database Schema Design**

#### **Core Tables**
```sql
-- Users and accounts
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    subscription_status VARCHAR(50),
    technical_expertise JSONB
);

-- LinkedIn integration
CREATE TABLE linkedin_accounts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    linkedin_id VARCHAR(255),
    access_token TEXT ENCRYPTED,
    profile_data JSONB,
    connected_at TIMESTAMP DEFAULT NOW()
);

-- Content management
CREATE TABLE content_posts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    status VARCHAR(50), -- draft, scheduled, posted
    scheduled_for TIMESTAMP,
    posted_at TIMESTAMP,
    performance_data JSONB
);

-- Lead tracking
CREATE TABLE leads (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    post_id UUID REFERENCES content_posts(id),
    linkedin_profile_url VARCHAR(500),
    inquiry_text TEXT,
    score INTEGER,
    status VARCHAR(50), -- new, contacted, qualified, converted
    detected_at TIMESTAMP DEFAULT NOW()
);
```

#### **Multi-Tenant Isolation**
- **Row-Level Security**: All queries filtered by user_id
- **Database Connection Pooling**: Efficient resource usage
- **Data Encryption**: Sensitive data encrypted at rest
- **Audit Logging**: Track all user actions for security

### **External Integrations**

#### **LinkedIn API Integration**
```python
# LinkedIn OAuth Flow
class LinkedInAuth:
    def authorize_user(self, user_id: str) -> str:
        # Generate LinkedIn OAuth URL
        # Handle callback and store tokens
        # Validate permissions and profile access
        
    def refresh_token(self, user_id: str) -> bool:
        # Automatic token refresh before expiration
        # Handle rate limiting and API errors
```

#### **Content Posting System**
```python
# Automated posting with queue system
class ContentScheduler:
    def schedule_post(self, user_id: str, content: str, 
                     scheduled_time: datetime) -> str:
        # Add to job queue with user isolation
        # Handle LinkedIn rate limits
        # Retry logic for failed posts
        
    def post_to_linkedin(self, user_id: str, content: str) -> str:
        # Make LinkedIn API call
        # Track posting success/failure
        # Update content status in database
```

### **Core Business Logic**

#### **Content Generation Engine**
```python
# Simplified version of Synapse content algorithms
class ContentEngine:
    def generate_content(self, user_expertise: List[str], 
                        topic_preferences: Dict) -> str:
        # Use proven templates from €290K pipeline
        # Personalize based on user's technical expertise
        # Apply engagement optimization rules
        
    def optimize_posting_time(self, user_id: str) -> datetime:
        # Analyze historical engagement patterns
        # Account for audience timezone and behavior
        # Return optimal posting time
```

#### **Lead Detection System**
```python
# NLP-based inquiry detection
class LeadDetector:
    def analyze_engagement(self, post_id: str) -> List[Lead]:
        # Process comments and reactions
        # Apply proven inquiry detection algorithms
        # Score leads based on qualification criteria
        
    def send_notification(self, user_id: str, lead: Lead) -> None:
        # Real-time notifications for high-score leads
        # Email, SMS, or push notification options
        # Avoid notification fatigue with smart filtering
```

### **Security Architecture**

#### **Authentication & Authorization**
- **JWT Tokens**: Stateless authentication with refresh tokens
- **OAuth Integration**: Secure LinkedIn account connection
- **Role-Based Access**: User roles and permissions system
- **Session Management**: Secure session handling and timeout

#### **Data Protection**
- **Encryption at Rest**: All sensitive data encrypted in database
- **Encryption in Transit**: HTTPS/TLS for all API communications
- **API Rate Limiting**: Prevent abuse and ensure fair usage
- **Input Validation**: Comprehensive validation and sanitization

### **Infrastructure & Deployment**

#### **Development Environment**
```yaml
# docker-compose.yml for local development
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/techlead
  
  database:
    image: postgres:15
    environment:
      - POSTGRES_DB=techlead
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
  
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

#### **Production Infrastructure**
- **Frontend**: Vercel or Netlify for static site hosting
- **Backend**: Railway, Render, or AWS ECS for API hosting
- **Database**: Managed PostgreSQL (Railway, PlanetScale, or AWS RDS)
- **Cache**: Managed Redis (Railway, Upstash, or AWS ElastiCache)
- **Monitoring**: Sentry for error tracking, Datadog for metrics

### **Scalability Considerations**

#### **Performance Optimization**
- **Database Indexing**: Optimized queries for user filtering
- **Caching Strategy**: Redis for frequently accessed data
- **CDN Integration**: Static assets served via CloudFlare
- **Background Jobs**: Async processing for content and analysis

#### **Horizontal Scaling**
- **Stateless API**: Backend can be scaled horizontally
- **Database Read Replicas**: Separate read/write operations
- **Queue Workers**: Scale job processing based on load
- **Load Balancing**: Distribute traffic across multiple instances

### **Development Workflow**

#### **Code Organization**
```
techlead-autopilot/
├── frontend/           # Next.js application
├── backend/            # FastAPI or Express application
├── shared/             # Shared types and utilities
├── docs/               # 12 core business documents
├── deploy/             # Infrastructure and deployment
└── tests/              # Automated testing suite
```

#### **Quality Assurance**
- **Type Safety**: TypeScript for frontend, Python/Node.js for backend
- **Testing**: Unit tests, integration tests, E2E tests
- **Code Review**: All changes require review before deployment
- **Automated CI/CD**: Automated testing and deployment pipeline

This architecture balances simplicity with scalability, ensuring we can serve thousands of customers while maintaining the flexibility to iterate and improve based on customer feedback.