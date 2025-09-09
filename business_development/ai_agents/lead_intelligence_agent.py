"""Lead Intelligence Agent for Epic 17 - Autonomous Business Development.

Provides advanced prospect research and qualification with:
- Deep company and contact research automation
- AI-powered lead scoring and qualification
- Intent signal detection and analysis
- Competitive landscape mapping for prospects
- Revenue potential and timing assessment
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LeadScore(Enum):
    """Lead scoring levels."""
    HOT = "hot"                    # Ready to buy, high priority
    WARM = "warm"                  # Interested, needs nurturing  
    QUALIFIED = "qualified"        # Meets criteria, needs development
    COLD = "cold"                  # Early stage, long-term nurturing
    UNQUALIFIED = "unqualified"    # Does not meet criteria


class CompanySize(Enum):
    """Company size categories."""
    STARTUP = "startup"            # <50 employees
    SMALL = "small"               # 50-200 employees
    MEDIUM = "medium"             # 200-1000 employees
    LARGE = "large"               # 1000-10000 employees
    ENTERPRISE = "enterprise"      # 10000+ employees
    FORTUNE_500 = "fortune_500"    # Fortune 500 company


class BuyingIntent(Enum):
    """Buying intent signals."""
    HIGH = "high"                 # Strong buying signals
    MODERATE = "moderate"         # Some buying signals
    LOW = "low"                  # Limited signals
    RESEARCH = "research"         # Information gathering phase
    UNKNOWN = "unknown"          # No clear signals


class DecisionTimeframe(Enum):
    """Expected decision timeframe."""
    IMMEDIATE = "immediate"       # <30 days
    SHORT_TERM = "short_term"     # 1-3 months
    MEDIUM_TERM = "medium_term"   # 3-6 months
    LONG_TERM = "long_term"       # 6-12 months
    FUTURE = "future"            # >12 months


@dataclass
class ContactProfile:
    """Profile of individual contact within prospect company."""
    contact_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    title: str = ""
    department: str = ""
    seniority_level: str = ""  # c_level, vp, director, manager, individual
    
    # Contact information
    email: str = ""
    phone: str = ""
    linkedin_profile: str = ""
    direct_mail_address: str = ""
    
    # Influence and decision making
    decision_making_authority: str = ""  # decision_maker, influencer, user, blocker
    budget_authority: bool = False
    technical_authority: bool = False
    influence_score: float = 0.0  # 0-1 scale
    
    # Engagement history
    engagement_history: List[Dict[str, Any]] = field(default_factory=list)
    preferred_communication: str = "email"  # email, phone, linkedin, in_person
    best_contact_times: List[str] = field(default_factory=list)
    response_rate: float = 0.0
    
    # Intelligence
    interests: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    recent_activities: List[str] = field(default_factory=list)
    social_media_activity: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    last_updated: str = ""
    confidence_score: float = 0.0
    data_sources: List[str] = field(default_factory=list)


@dataclass
class ProspectProfile:
    """Comprehensive prospect company profile."""
    prospect_id: str = field(default_factory=lambda: str(uuid4()))
    company_name: str = ""
    company_size: CompanySize = CompanySize.MEDIUM
    industry: str = ""
    sub_industry: str = ""
    
    # Company details
    headquarters_location: str = ""
    office_locations: List[str] = field(default_factory=list)
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    funding_status: str = ""  # public, private, startup, etc.
    recent_funding: Optional[Dict[str, Any]] = None
    
    # Business intelligence
    business_model: str = ""
    primary_products: List[str] = field(default_factory=list)
    target_customers: List[str] = field(default_factory=list)
    key_competitors: List[str] = field(default_factory=list)
    market_position: str = ""
    
    # Technology profile
    technology_stack: List[str] = field(default_factory=list)
    current_solutions: Dict[str, str] = field(default_factory=dict)  # category -> solution
    technology_maturity: str = ""  # early_adopter, mainstream, laggard
    digital_transformation_stage: str = ""
    
    # Financial health
    financial_health_score: float = 0.0  # 0-1 scale
    growth_trajectory: str = ""  # growing, stable, declining
    profitability_status: str = ""
    recent_financial_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Buying signals and intent
    buying_intent: BuyingIntent = BuyingIntent.UNKNOWN
    intent_signals: List[str] = field(default_factory=list)
    decision_timeframe: DecisionTimeframe = DecisionTimeframe.UNKNOWN
    budget_range: Optional[Tuple[float, float]] = None
    
    # Organizational intelligence
    org_structure: Dict[str, Any] = field(default_factory=dict)
    decision_making_process: str = ""
    typical_sales_cycle: str = ""  # 30_days, 60_days, 90_days, 180_days, etc.
    procurement_process: str = ""
    
    # Contacts and relationships
    contacts: List[ContactProfile] = field(default_factory=list)
    champion_contacts: List[str] = field(default_factory=list)  # contact_ids
    blocker_contacts: List[str] = field(default_factory=list)  # contact_ids
    existing_relationships: Dict[str, str] = field(default_factory=dict)
    
    # Opportunity assessment
    opportunity_score: float = 0.0  # 0-1 scale
    fit_score: float = 0.0  # How well they fit our ICP
    win_probability: float = 0.0
    estimated_deal_size: Optional[float] = None
    estimated_annual_value: Optional[float] = None
    
    # Competitive landscape
    competitive_threats: List[str] = field(default_factory=list)
    incumbent_solutions: List[str] = field(default_factory=list)
    switching_barriers: List[str] = field(default_factory=list)
    competitive_advantages: List[str] = field(default_factory=list)
    
    # Engagement strategy
    recommended_approach: str = ""
    key_value_propositions: List[str] = field(default_factory=list)
    personalization_insights: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Metadata
    lead_score: LeadScore = LeadScore.COLD
    created_date: str = ""
    last_updated: str = ""
    next_action_date: str = ""
    assigned_rep: str = ""
    data_confidence: float = 0.0
    research_sources: List[str] = field(default_factory=list)


class ResearchResult(BaseModel):
    """Result of prospect research."""
    research_id: str = Field(default_factory=lambda: str(uuid4()))
    prospect_id: str = ""
    research_type: str = ""  # company_research, contact_research, intent_analysis
    
    # Research findings
    key_findings: List[str] = Field(default_factory=list)
    data_collected: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Intelligence insights
    opportunities_identified: List[str] = Field(default_factory=list)
    risks_identified: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    
    # Metadata
    research_timestamp: str = Field(default_factory=lambda: str(datetime.now()))
    research_duration: float = Field(default=0.0)
    sources_used: List[str] = Field(default_factory=list)
    researcher: str = "LeadIntelligenceAgent"


class LeadIntelligenceAgent:
    """Advanced AI agent for prospect research and lead qualification."""
    
    def __init__(
        self,
        graph_repository=None,
        vector_store=None,
        llm_service=None,
        web_research_service=None,
        social_media_service=None,
        financial_data_service=None,
        competitive_analyzer=None
    ):
        """Initialize the lead intelligence agent."""
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.web_research_service = web_research_service
        self.social_media_service = social_media_service
        self.financial_data_service = financial_data_service
        self.competitive_analyzer = competitive_analyzer
        
        # Prospect database
        self.prospect_profiles: Dict[str, ProspectProfile] = {}
        self.research_cache: Dict[str, ResearchResult] = {}
        
        # Intelligence configuration
        self.research_sources = self._initialize_research_sources()
        self.qualification_criteria = self._initialize_qualification_criteria()
        self.scoring_models = self._initialize_scoring_models()
        
        # Performance tracking
        self.agent_stats = {
            "prospects_researched": 0,
            "contacts_profiled": 0,
            "research_accuracy": 0.0,
            "qualification_accuracy": 0.0,
            "avg_research_time": 0.0,
            "conversion_to_opportunity": 0.0
        }
    
    def _initialize_research_sources(self) -> Dict[str, Dict[str, Any]]:
        """Initialize research data sources."""
        return {
            "company_websites": {
                "priority": 1,
                "reliability": 0.9,
                "data_types": ["company_info", "products", "news", "leadership"]
            },
            "linkedin": {
                "priority": 2,
                "reliability": 0.8,
                "data_types": ["contacts", "company_updates", "employee_info", "network"]
            },
            "financial_databases": {
                "priority": 3,
                "reliability": 0.95,
                "data_types": ["revenue", "funding", "financial_health", "growth"]
            },
            "news_sources": {
                "priority": 4,
                "reliability": 0.7,
                "data_types": ["company_news", "industry_trends", "executive_changes"]
            },
            "technology_databases": {
                "priority": 5,
                "reliability": 0.8,
                "data_types": ["tech_stack", "software_usage", "it_infrastructure"]
            },
            "social_media": {
                "priority": 6,
                "reliability": 0.6,
                "data_types": ["sentiment", "engagement", "brand_mentions", "events"]
            }
        }
    
    def _initialize_qualification_criteria(self) -> Dict[str, Dict[str, Any]]:
        """Initialize lead qualification criteria."""
        return {
            "company_size": {
                "weight": 0.2,
                "criteria": {
                    CompanySize.FORTUNE_500: 1.0,
                    CompanySize.ENTERPRISE: 0.9,
                    CompanySize.LARGE: 0.7,
                    CompanySize.MEDIUM: 0.5,
                    CompanySize.SMALL: 0.2,
                    CompanySize.STARTUP: 0.1
                }
            },
            "industry_fit": {
                "weight": 0.15,
                "target_industries": [
                    "technology", "financial_services", "healthcare", 
                    "manufacturing", "consulting", "government"
                ]
            },
            "budget_potential": {
                "weight": 0.2,
                "minimum_budget": 100000,  # $100K minimum deal size
                "ideal_budget": 500000     # $500K+ ideal deal size
            },
            "technology_maturity": {
                "weight": 0.15,
                "criteria": {
                    "early_adopter": 1.0,
                    "mainstream": 0.8,
                    "laggard": 0.4
                }
            },
            "buying_intent": {
                "weight": 0.2,
                "criteria": {
                    BuyingIntent.HIGH: 1.0,
                    BuyingIntent.MODERATE: 0.7,
                    BuyingIntent.LOW: 0.4,
                    BuyingIntent.RESEARCH: 0.6,
                    BuyingIntent.UNKNOWN: 0.3
                }
            },
            "decision_timeframe": {
                "weight": 0.1,
                "criteria": {
                    DecisionTimeframe.IMMEDIATE: 1.0,
                    DecisionTimeframe.SHORT_TERM: 0.9,
                    DecisionTimeframe.MEDIUM_TERM: 0.7,
                    DecisionTimeframe.LONG_TERM: 0.4,
                    DecisionTimeframe.FUTURE: 0.2
                }
            }
        }
    
    def _initialize_scoring_models(self) -> Dict[str, Dict[str, Any]]:
        """Initialize scoring models for lead assessment."""
        return {
            "lead_score": {
                "factors": [
                    "company_size", "industry_fit", "budget_potential", 
                    "technology_maturity", "buying_intent", "decision_timeframe"
                ],
                "weights": [0.2, 0.15, 0.2, 0.15, 0.2, 0.1]
            },
            "fit_score": {
                "factors": [
                    "ideal_customer_profile", "use_case_alignment", 
                    "technology_compatibility", "geographic_alignment"
                ],
                "weights": [0.3, 0.3, 0.2, 0.2]
            },
            "opportunity_score": {
                "factors": [
                    "lead_score", "fit_score", "competitive_position", 
                    "relationship_strength", "timing_alignment"
                ],
                "weights": [0.3, 0.25, 0.2, 0.15, 0.1]
            }
        }
    
    async def research_prospect(
        self,
        company_name: str,
        additional_context: Optional[Dict[str, Any]] = None,
        research_depth: str = "comprehensive"  # basic, standard, comprehensive
    ) -> ProspectProfile:
        """Conduct comprehensive prospect research."""
        start_time = asyncio.get_event_loop().time()
        
        # Create or get existing prospect profile
        existing_profile = self._find_existing_prospect(company_name)
        if existing_profile:
            profile = existing_profile
        else:
            profile = ProspectProfile(
                company_name=company_name,
                created_date=str(datetime.now())
            )
        
        try:
            # Phase 1: Company research
            company_research = await self._research_company_basics(company_name, research_depth)
            self._update_profile_with_company_research(profile, company_research)
            
            # Phase 2: Contact research
            if research_depth in ["standard", "comprehensive"]:
                contact_research = await self._research_key_contacts(profile)
                profile.contacts = contact_research
            
            # Phase 3: Intent analysis
            if research_depth == "comprehensive":
                intent_analysis = await self._analyze_buying_intent(profile)
                self._update_profile_with_intent_analysis(profile, intent_analysis)
            
            # Phase 4: Competitive landscape
            competitive_analysis = await self._analyze_competitive_landscape(profile)
            self._update_profile_with_competitive_analysis(profile, competitive_analysis)
            
            # Phase 5: Opportunity assessment
            opportunity_assessment = await self._assess_opportunity(profile)
            self._update_profile_with_opportunity_assessment(profile, opportunity_assessment)
            
            # Phase 6: Lead scoring and qualification
            profile.lead_score = self._calculate_lead_score(profile)
            profile.fit_score = self._calculate_fit_score(profile)
            profile.opportunity_score = self._calculate_opportunity_score(profile)
            profile.win_probability = self._calculate_win_probability(profile)
            
            # Phase 7: Generate recommendations
            recommendations = await self._generate_engagement_recommendations(profile)
            profile.recommended_approach = recommendations.get("approach", "")
            profile.key_value_propositions = recommendations.get("value_props", [])
            profile.personalization_insights = recommendations.get("personalization", [])
            
            # Update metadata
            profile.last_updated = str(datetime.now())
            profile.data_confidence = self._calculate_data_confidence(profile)
            
            # Store profile
            self.prospect_profiles[profile.prospect_id] = profile
            
            # Update performance stats
            research_time = asyncio.get_event_loop().time() - start_time
            self._update_agent_stats(profile, research_time)
            
            logger.info(f"Prospect research completed for {company_name}: "
                       f"Score: {profile.lead_score.value}, "
                       f"Confidence: {profile.data_confidence:.2f}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error researching prospect {company_name}: {str(e)}")
            profile.data_confidence = 0.2
            profile.lead_score = LeadScore.UNQUALIFIED
            return profile
    
    def _find_existing_prospect(self, company_name: str) -> Optional[ProspectProfile]:
        """Find existing prospect profile by company name."""
        for profile in self.prospect_profiles.values():
            if profile.company_name.lower() == company_name.lower():
                return profile
        return None
    
    async def _research_company_basics(
        self, 
        company_name: str, 
        depth: str
    ) -> Dict[str, Any]:
        """Research basic company information."""
        research_data = {
            "company_name": company_name,
            "industry": "Technology",  # Mock data
            "employee_count": np.random.randint(500, 10000),
            "headquarters_location": np.random.choice(["San Francisco", "New York", "Seattle"]),
            "annual_revenue": np.random.randint(10, 500) * 1000000,  # $10M - $500M
            "funding_status": np.random.choice(["public", "private", "startup"]),
            "business_model": "SaaS"
        }
        
        # Use web research service if available
        if self.web_research_service:
            try:
                web_data = await self.web_research_service.research_company(company_name)
                research_data.update(web_data)
            except Exception as e:
                logger.warning(f"Web research failed for {company_name}: {str(e)}")
        
        # Use financial data service for public companies
        if self.financial_data_service and research_data.get("funding_status") == "public":
            try:
                financial_data = await self.financial_data_service.get_company_data(company_name)
                research_data.update(financial_data)
            except Exception as e:
                logger.warning(f"Financial research failed for {company_name}: {str(e)}")
        
        return research_data
    
    def _update_profile_with_company_research(
        self, 
        profile: ProspectProfile, 
        research_data: Dict[str, Any]
    ):
        """Update prospect profile with company research data."""
        # Map research data to profile fields
        field_mappings = {
            "industry": "industry",
            "employee_count": "employee_count", 
            "headquarters_location": "headquarters_location",
            "annual_revenue": "annual_revenue",
            "funding_status": "funding_status",
            "business_model": "business_model"
        }
        
        for research_key, profile_key in field_mappings.items():
            if research_key in research_data:
                setattr(profile, profile_key, research_data[research_key])
        
        # Determine company size
        if profile.employee_count:
            if profile.employee_count >= 10000:
                profile.company_size = CompanySize.ENTERPRISE
            elif profile.employee_count >= 1000:
                profile.company_size = CompanySize.LARGE
            elif profile.employee_count >= 200:
                profile.company_size = CompanySize.MEDIUM
            elif profile.employee_count >= 50:
                profile.company_size = CompanySize.SMALL
            else:
                profile.company_size = CompanySize.STARTUP
        
        # Check if Fortune 500
        if profile.annual_revenue and profile.annual_revenue > 5_000_000_000:  # $5B+
            profile.company_size = CompanySize.FORTUNE_500
        
        # Add to research sources
        profile.research_sources.extend(["company_research", "web_research", "financial_research"])
    
    async def _research_key_contacts(self, profile: ProspectProfile) -> List[ContactProfile]:
        """Research key contacts within the prospect company."""
        contacts = []
        
        # Mock contact research (would use LinkedIn, company website, etc.)
        key_roles = [
            ("Chief Technology Officer", "c_level", "technology"),
            ("VP of Engineering", "vp", "technology"),
            ("Chief Information Officer", "c_level", "technology"),
            ("Director of IT", "director", "technology"),
            ("Chief Financial Officer", "c_level", "finance"),
            ("VP of Operations", "vp", "operations")
        ]
        
        for role, seniority, department in key_roles[:4]:  # Limit to top 4 contacts
            contact = ContactProfile(
                name=f"Contact at {profile.company_name}",
                title=role,
                department=department,
                seniority_level=seniority,
                decision_making_authority="decision_maker" if seniority == "c_level" else "influencer",
                budget_authority=seniority == "c_level" and department in ["finance", "technology"],
                technical_authority=department == "technology",
                influence_score=0.9 if seniority == "c_level" else 0.7,
                preferred_communication="email",
                confidence_score=0.7
            )
            
            # Add mock engagement insights
            contact.interests = ["digital_transformation", "efficiency", "innovation"]
            contact.pain_points = ["legacy_systems", "scalability", "costs"]
            
            contacts.append(contact)
        
        return contacts
    
    async def _analyze_buying_intent(self, profile: ProspectProfile) -> Dict[str, Any]:
        """Analyze buying intent signals for the prospect."""
        intent_analysis = {
            "intent_level": BuyingIntent.MODERATE,
            "signals": [],
            "timeframe": DecisionTimeframe.MEDIUM_TERM,
            "budget_indicators": []
        }
        
        # Analyze various intent signals
        signals = []
        
        # Technology adoption signals
        if profile.technology_maturity == "early_adopter":
            signals.append("Early technology adopter")
            intent_analysis["intent_level"] = BuyingIntent.HIGH
        
        # Growth signals
        if profile.growth_trajectory == "growing":
            signals.append("Company in growth phase")
        
        # Financial health signals
        if profile.financial_health_score > 0.7:
            signals.append("Strong financial position")
            intent_analysis["budget_indicators"].append("Healthy financials support investment")
        
        # Recent funding signals
        if profile.recent_funding:
            signals.append("Recent funding secured")
            intent_analysis["intent_level"] = BuyingIntent.HIGH
            intent_analysis["timeframe"] = DecisionTimeframe.SHORT_TERM
        
        # Industry trend signals
        if profile.industry in ["technology", "financial_services"]:
            signals.append("Industry undergoing digital transformation")
        
        intent_analysis["signals"] = signals
        
        return intent_analysis
    
    def _update_profile_with_intent_analysis(
        self, 
        profile: ProspectProfile, 
        intent_analysis: Dict[str, Any]
    ):
        """Update profile with buying intent analysis."""
        profile.buying_intent = intent_analysis.get("intent_level", BuyingIntent.UNKNOWN)
        profile.intent_signals = intent_analysis.get("signals", [])
        profile.decision_timeframe = intent_analysis.get("timeframe", DecisionTimeframe.UNKNOWN)
        
        # Estimate budget range based on company size and intent
        if profile.annual_revenue:
            # Estimate technology budget as 3-8% of revenue
            tech_budget = profile.annual_revenue * np.random.uniform(0.03, 0.08)
            
            # Our solution could be 5-20% of tech budget
            min_budget = tech_budget * 0.05
            max_budget = tech_budget * 0.20
            profile.budget_range = (min_budget, max_budget)
    
    async def _analyze_competitive_landscape(self, profile: ProspectProfile) -> Dict[str, Any]:
        """Analyze competitive landscape for the prospect."""
        competitive_analysis = {
            "threats": [],
            "incumbents": [],
            "advantages": [],
            "barriers": []
        }
        
        # Use competitive analyzer if available
        if self.competitive_analyzer:
            try:
                # Get competitive intelligence for prospect's industry
                analysis_result = await self.competitive_analyzer.perform_competitive_analysis(
                    analysis_type="market_overview",
                    market_segments=[profile.industry]
                )
                
                competitive_analysis["threats"] = [
                    threat["title"] for threat in analysis_result.risk_alerts[:3]
                ]
                competitive_analysis["advantages"] = analysis_result.differentiation_opportunities[:3]
                
            except Exception as e:
                logger.warning(f"Competitive analysis failed: {str(e)}")
        
        # Add default competitive considerations
        competitive_analysis["incumbents"] = [
            "Legacy enterprise solutions",
            "Custom internal systems", 
            "Competitor solutions"
        ]
        
        competitive_analysis["barriers"] = [
            "Existing system integration",
            "Change management resistance",
            "Procurement process complexity"
        ]
        
        return competitive_analysis
    
    def _update_profile_with_competitive_analysis(
        self, 
        profile: ProspectProfile, 
        competitive_analysis: Dict[str, Any]
    ):
        """Update profile with competitive analysis."""
        profile.competitive_threats = competitive_analysis.get("threats", [])
        profile.incumbent_solutions = competitive_analysis.get("incumbents", [])
        profile.competitive_advantages = competitive_analysis.get("advantages", [])
        profile.switching_barriers = competitive_analysis.get("barriers", [])
    
    async def _assess_opportunity(self, profile: ProspectProfile) -> Dict[str, Any]:
        """Assess the sales opportunity for the prospect."""
        opportunity_assessment = {
            "deal_size_estimate": None,
            "annual_value_estimate": None,
            "win_probability_factors": [],
            "risk_factors": []
        }
        
        # Estimate deal size based on company characteristics
        base_deal_size = 50000  # Base deal size
        
        # Size multiplier
        size_multipliers = {
            CompanySize.STARTUP: 0.5,
            CompanySize.SMALL: 1.0,
            CompanySize.MEDIUM: 2.0,
            CompanySize.LARGE: 5.0,
            CompanySize.ENTERPRISE: 10.0,
            CompanySize.FORTUNE_500: 20.0
        }
        
        size_multiplier = size_multipliers.get(profile.company_size, 1.0)
        estimated_deal_size = base_deal_size * size_multiplier
        
        # Adjust for intent and urgency
        intent_multipliers = {
            BuyingIntent.HIGH: 1.5,
            BuyingIntent.MODERATE: 1.2,
            BuyingIntent.LOW: 1.0,
            BuyingIntent.RESEARCH: 0.8,
            BuyingIntent.UNKNOWN: 0.7
        }
        
        intent_multiplier = intent_multipliers.get(profile.buying_intent, 1.0)
        estimated_deal_size *= intent_multiplier
        
        opportunity_assessment["deal_size_estimate"] = estimated_deal_size
        opportunity_assessment["annual_value_estimate"] = estimated_deal_size * 1.2  # Assume 20% annual growth
        
        # Win probability factors
        win_factors = []
        if profile.buying_intent in [BuyingIntent.HIGH, BuyingIntent.MODERATE]:
            win_factors.append("Strong buying intent")
        
        if profile.company_size in [CompanySize.ENTERPRISE, CompanySize.FORTUNE_500]:
            win_factors.append("Large enterprise target")
        
        if profile.financial_health_score > 0.7:
            win_factors.append("Strong financial position")
        
        opportunity_assessment["win_probability_factors"] = win_factors
        
        # Risk factors
        risk_factors = []
        if len(profile.competitive_threats) > 2:
            risk_factors.append("High competitive pressure")
        
        if profile.decision_timeframe == DecisionTimeframe.LONG_TERM:
            risk_factors.append("Long decision timeline")
        
        if len(profile.switching_barriers) > 3:
            risk_factors.append("High switching barriers")
        
        opportunity_assessment["risk_factors"] = risk_factors
        
        return opportunity_assessment
    
    def _update_profile_with_opportunity_assessment(
        self, 
        profile: ProspectProfile, 
        opportunity_assessment: Dict[str, Any]
    ):
        """Update profile with opportunity assessment."""
        profile.estimated_deal_size = opportunity_assessment.get("deal_size_estimate")
        profile.estimated_annual_value = opportunity_assessment.get("annual_value_estimate")
        profile.risk_factors = opportunity_assessment.get("risk_factors", [])
    
    def _calculate_lead_score(self, profile: ProspectProfile) -> LeadScore:
        """Calculate lead score based on qualification criteria."""
        criteria = self.qualification_criteria
        total_score = 0.0
        
        # Company size score
        size_score = criteria["company_size"]["criteria"].get(profile.company_size, 0.5)
        total_score += size_score * criteria["company_size"]["weight"]
        
        # Industry fit score
        industry_fit = 1.0 if profile.industry in criteria["industry_fit"]["target_industries"] else 0.5
        total_score += industry_fit * criteria["industry_fit"]["weight"]
        
        # Budget potential score
        if profile.budget_range:
            min_budget = profile.budget_range[0]
            budget_score = min(min_budget / criteria["budget_potential"]["minimum_budget"], 1.0)
            total_score += budget_score * criteria["budget_potential"]["weight"]
        
        # Technology maturity score
        tech_score = criteria["technology_maturity"]["criteria"].get(profile.technology_maturity, 0.5)
        total_score += tech_score * criteria["technology_maturity"]["weight"]
        
        # Buying intent score
        intent_score = criteria["buying_intent"]["criteria"].get(profile.buying_intent, 0.3)
        total_score += intent_score * criteria["buying_intent"]["weight"]
        
        # Decision timeframe score
        timeframe_score = criteria["decision_timeframe"]["criteria"].get(profile.decision_timeframe, 0.5)
        total_score += timeframe_score * criteria["decision_timeframe"]["weight"]
        
        # Map score to lead score enum
        if total_score >= 0.8:
            return LeadScore.HOT
        elif total_score >= 0.6:
            return LeadScore.WARM
        elif total_score >= 0.4:
            return LeadScore.QUALIFIED
        elif total_score >= 0.2:
            return LeadScore.COLD
        else:
            return LeadScore.UNQUALIFIED
    
    def _calculate_fit_score(self, profile: ProspectProfile) -> float:
        """Calculate how well prospect fits ideal customer profile."""
        fit_factors = {
            "company_size": 1.0 if profile.company_size in [CompanySize.ENTERPRISE, CompanySize.FORTUNE_500] else 0.7,
            "industry": 1.0 if profile.industry in ["technology", "financial_services"] else 0.6,
            "growth_stage": 1.0 if profile.growth_trajectory == "growing" else 0.7,
            "financial_health": profile.financial_health_score or 0.5
        }
        
        weights = [0.3, 0.3, 0.2, 0.2]
        fit_score = sum(factor * weight for factor, weight in zip(fit_factors.values(), weights))
        
        return min(fit_score, 1.0)
    
    def _calculate_opportunity_score(self, profile: ProspectProfile) -> float:
        """Calculate overall opportunity score."""
        factors = {
            "lead_score_numeric": self._lead_score_to_numeric(profile.lead_score),
            "fit_score": profile.fit_score,
            "deal_size": min((profile.estimated_deal_size or 0) / 500000, 1.0),  # Normalize to $500K
            "win_probability_factors": len(profile.risk_factors) / 10.0,  # Rough estimate
            "competitive_position": 1.0 - (len(profile.competitive_threats) / 5.0)  # Fewer threats = better
        }
        
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        opportunity_score = sum(factor * weight for factor, weight in zip(factors.values(), weights))
        
        return min(max(opportunity_score, 0.0), 1.0)
    
    def _lead_score_to_numeric(self, lead_score: LeadScore) -> float:
        """Convert lead score enum to numeric value."""
        mapping = {
            LeadScore.HOT: 1.0,
            LeadScore.WARM: 0.8,
            LeadScore.QUALIFIED: 0.6,
            LeadScore.COLD: 0.3,
            LeadScore.UNQUALIFIED: 0.1
        }
        return mapping.get(lead_score, 0.1)
    
    def _calculate_win_probability(self, profile: ProspectProfile) -> float:
        """Calculate probability of winning the deal."""
        base_probability = 0.2  # Base 20% win rate
        
        # Adjust based on lead score
        score_multipliers = {
            LeadScore.HOT: 2.5,
            LeadScore.WARM: 2.0,
            LeadScore.QUALIFIED: 1.5,
            LeadScore.COLD: 1.0,
            LeadScore.UNQUALIFIED: 0.3
        }
        
        multiplier = score_multipliers.get(profile.lead_score, 1.0)
        win_probability = base_probability * multiplier
        
        # Adjust for competitive factors
        if len(profile.competitive_threats) > 2:
            win_probability *= 0.8
        
        # Adjust for relationship strength
        champion_contacts = len([c for c in profile.contacts if c.influence_score > 0.8])
        if champion_contacts > 0:
            win_probability *= (1.0 + champion_contacts * 0.2)
        
        return min(win_probability, 0.9)  # Cap at 90%
    
    async def _generate_engagement_recommendations(
        self, 
        profile: ProspectProfile
    ) -> Dict[str, Any]:
        """Generate engagement strategy recommendations."""
        recommendations = {
            "approach": "",
            "value_props": [],
            "personalization": [],
            "channels": [],
            "timing": ""
        }
        
        # Determine approach based on lead score and company characteristics
        if profile.lead_score == LeadScore.HOT:
            recommendations["approach"] = "Direct executive engagement with solution demonstration"
        elif profile.lead_score == LeadScore.WARM:
            recommendations["approach"] = "Multi-touch nurturing with value-focused content"
        elif profile.lead_score == LeadScore.QUALIFIED:
            recommendations["approach"] = "Educational content strategy with gradual engagement"
        else:
            recommendations["approach"] = "Long-term nurturing with industry insights"
        
        # Value propositions based on company characteristics
        value_props = []
        if profile.company_size in [CompanySize.ENTERPRISE, CompanySize.FORTUNE_500]:
            value_props.append("Enterprise-scale performance and reliability")
            value_props.append("Advanced security and compliance capabilities")
        
        if profile.growth_trajectory == "growing":
            value_props.append("Scalable solution that grows with your business")
        
        if "efficiency" in [pain for contact in profile.contacts for pain in contact.pain_points]:
            value_props.append("Significant operational efficiency improvements")
        
        recommendations["value_props"] = value_props
        
        # Personalization insights
        personalization = []
        if profile.industry:
            personalization.append(f"Industry-specific examples from {profile.industry} sector")
        
        if profile.recent_funding:
            personalization.append("Focus on ROI and growth acceleration messaging")
        
        for contact in profile.contacts:
            if contact.department == "technology":
                personalization.append("Technical architecture and integration discussions")
            elif contact.department == "finance":
                personalization.append("Cost savings and financial impact analysis")
        
        recommendations["personalization"] = personalization
        
        # Recommended channels
        channels = ["email", "linkedin"]
        if profile.company_size in [CompanySize.ENTERPRISE, CompanySize.FORTUNE_500]:
            channels.extend(["direct_mail", "executive_briefing"])
        
        recommendations["channels"] = channels
        
        # Timing recommendations
        if profile.decision_timeframe == DecisionTimeframe.IMMEDIATE:
            recommendations["timing"] = "Immediate follow-up within 24-48 hours"
        elif profile.decision_timeframe == DecisionTimeframe.SHORT_TERM:
            recommendations["timing"] = "Weekly touchpoints over next month"
        else:
            recommendations["timing"] = "Monthly value-add communications"
        
        return recommendations
    
    def _calculate_data_confidence(self, profile: ProspectProfile) -> float:
        """Calculate confidence score for prospect data."""
        confidence_factors = {
            "basic_info": 1.0 if profile.company_name and profile.industry else 0.0,
            "contact_data": len(profile.contacts) / 5.0,  # Target 5 contacts
            "financial_data": 1.0 if profile.annual_revenue else 0.5,
            "intent_data": len(profile.intent_signals) / 5.0,  # Target 5 signals
            "competitive_data": len(profile.competitive_threats) / 3.0,  # Target 3 threats
            "research_sources": len(profile.research_sources) / 6.0  # Target 6 sources
        }
        
        weights = [0.2, 0.2, 0.15, 0.15, 0.15, 0.15]
        confidence = sum(factor * weight for factor, weight in zip(confidence_factors.values(), weights))
        
        return min(confidence, 1.0)
    
    def _update_agent_stats(self, profile: ProspectProfile, research_time: float):
        """Update agent performance statistics."""
        self.agent_stats["prospects_researched"] += 1
        self.agent_stats["contacts_profiled"] += len(profile.contacts)
        
        # Update research time average
        count = self.agent_stats["prospects_researched"]
        old_time = self.agent_stats["avg_research_time"]
        new_time = ((old_time * (count - 1)) + research_time) / count
        self.agent_stats["avg_research_time"] = new_time
    
    def get_prospect_profile(self, prospect_id: str) -> Optional[ProspectProfile]:
        """Get prospect profile by ID."""
        return self.prospect_profiles.get(prospect_id)
    
    def list_prospects(
        self,
        lead_score: Optional[LeadScore] = None,
        company_size: Optional[CompanySize] = None,
        industry: Optional[str] = None
    ) -> List[ProspectProfile]:
        """List prospects with optional filtering."""
        prospects = list(self.prospect_profiles.values())
        
        if lead_score:
            prospects = [p for p in prospects if p.lead_score == lead_score]
        
        if company_size:
            prospects = [p for p in prospects if p.company_size == company_size]
        
        if industry:
            prospects = [p for p in prospects if p.industry.lower() == industry.lower()]
        
        return prospects
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        return {
            **self.agent_stats,
            "active_prospects": len(self.prospect_profiles),
            "research_sources": len(self.research_sources),
            "qualification_criteria": len(self.qualification_criteria)
        }
    
    async def update_prospect_data(self, prospect_id: str) -> bool:
        """Update prospect data with latest intelligence."""
        try:
            profile = self.prospect_profiles.get(prospect_id)
            if not profile:
                return False
            
            # Re-research company data
            company_research = await self._research_company_basics(profile.company_name, "standard")
            self._update_profile_with_company_research(profile, company_research)
            
            # Re-assess opportunity
            opportunity_assessment = await self._assess_opportunity(profile)
            self._update_profile_with_opportunity_assessment(profile, opportunity_assessment)
            
            # Recalculate scores
            profile.lead_score = self._calculate_lead_score(profile)
            profile.fit_score = self._calculate_fit_score(profile)
            profile.opportunity_score = self._calculate_opportunity_score(profile)
            profile.win_probability = self._calculate_win_probability(profile)
            
            # Update metadata
            profile.last_updated = str(datetime.now())
            profile.data_confidence = self._calculate_data_confidence(profile)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating prospect {prospect_id}: {str(e)}")
            return False