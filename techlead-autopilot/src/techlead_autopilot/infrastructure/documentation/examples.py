"""Example generator for OpenAPI documentation with realistic data."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class ExampleGenerator:
    """Generates realistic examples for API documentation.
    
    Creates comprehensive examples for:
    - Request/response payloads
    - Different content types and scenarios
    - Success and error responses  
    - Authentication flows
    - Rate limiting scenarios
    """
    
    def __init__(self):
        """Initialize example generator with realistic data."""
        self.sample_topics = [
            "Leadership in Tech: Building High-Performance Teams",
            "The Future of AI in Software Development",
            "Scaling Engineering Teams from 5 to 50",
            "Technical Debt: When and How to Address It",
            "DevOps Culture: Breaking Down Silos",
            "Code Reviews: Beyond Bug Catching",
            "Remote Team Management Best Practices",
            "Cloud Migration Strategy for Enterprises"
        ]
        
        self.sample_content_types = [
            "thought_leadership",
            "industry_insight", 
            "case_study",
            "technical_deep_dive",
            "career_advice",
            "team_management",
            "startup_story",
            "lessons_learned"
        ]
        
        self.sample_leads = [
            {
                "company": "TechCorp Inc.",
                "author": "Sarah Johnson",
                "title": "VP of Engineering",
                "inquiry": "We're struggling with scaling our development team. Could use some guidance on best practices.",
                "priority": "high"
            },
            {
                "company": "StartupXYZ",
                "author": "Mike Chen", 
                "title": "CTO",
                "inquiry": "Interested in your approach to technical debt management. We're facing similar challenges.",
                "priority": "medium"
            }
        ]
    
    def generate_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for a specific API operation.
        
        Args:
            path: API endpoint path
            method: HTTP method
            operation: OpenAPI operation definition
            
        Returns:
            Dictionary containing request and response examples
        """
        examples = {
            "request": {},
            "responses": {}
        }
        
        # Generate examples based on endpoint
        if "/content" in path:
            examples.update(self._generate_content_examples(path, method, operation))
        elif "/leads" in path:
            examples.update(self._generate_lead_examples(path, method, operation))
        elif "/analytics" in path:
            examples.update(self._generate_analytics_examples(path, method, operation))
        elif "/auth" in path:
            examples.update(self._generate_auth_examples(path, method, operation))
        elif "/scheduler" in path:
            examples.update(self._generate_scheduler_examples(path, method, operation))
        else:
            examples.update(self._generate_generic_examples(path, method, operation))
        
        return examples
    
    def _generate_content_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for content-related endpoints."""
        examples = {"request": {}, "responses": {}}
        
        if method == "post" and "generate" in path:
            # Content generation request
            examples["request"] = {
                "basic_thought_leadership": {
                    "summary": "Generate thought leadership content",
                    "description": "Generate a LinkedIn post about technical leadership",
                    "value": {
                        "topic": "Leadership in Tech: Building High-Performance Teams",
                        "content_type": "thought_leadership",
                        "target_audience": "engineering_leaders",
                        "tone": "professional",
                        "include_call_to_action": True,
                        "hashtags": ["#TechLeadership", "#EngineeringManagement", "#TeamBuilding"]
                    }
                },
                "technical_deep_dive": {
                    "summary": "Generate technical deep-dive content", 
                    "description": "Generate detailed technical content for expert audience",
                    "value": {
                        "topic": "The Future of AI in Software Development",
                        "content_type": "technical_deep_dive",
                        "target_audience": "senior_developers",
                        "tone": "analytical",
                        "include_call_to_action": False,
                        "hashtags": ["#AI", "#SoftwareDevelopment", "#MachineLearning"]
                    }
                }
            }
            
            # Content generation responses
            examples["responses"] = {
                "200": {
                    "successful_generation": {
                        "summary": "Successfully generated content",
                        "description": "Content generated with engagement predictions and metadata",
                        "value": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "content": {
                                "text": "Building high-performance engineering teams isn't just about hiring the best developers.\n\nIt's about creating psychological safety, establishing clear communication channels, and fostering a culture of continuous learning.\n\nIn my experience leading teams from 5 to 50 engineers, the most successful teams share these characteristics:\n\n🎯 Clear vision and goals\n🤝 Trust and psychological safety\n📚 Commitment to learning and growth\n⚡ Efficient communication processes\n🔄 Regular feedback loops\n\nWhat's been your experience? What makes engineering teams truly high-performing?\n\n#TechLeadership #EngineeringManagement #TeamBuilding",
                                "engagement_prediction": {
                                    "likes": 127,
                                    "comments": 23,
                                    "shares": 8,
                                    "consultation_probability": 0.73
                                },
                                "optimal_posting_times": [
                                    {
                                        "day": "tuesday",
                                        "time": "06:30",
                                        "timezone": "PST",
                                        "engagement_score": 0.89
                                    },
                                    {
                                        "day": "thursday", 
                                        "time": "06:30",
                                        "timezone": "PST",
                                        "engagement_score": 0.85
                                    }
                                ]
                            },
                            "metadata": {
                                "topic": "Leadership in Tech: Building High-Performance Teams",
                                "content_type": "thought_leadership",
                                "generated_at": "2024-01-15T10:30:00Z",
                                "word_count": 187,
                                "character_count": 1243,
                                "hashtag_count": 3,
                                "call_to_action": True
                            },
                            "status": "draft",
                            "organization_id": "org_123456789"
                        }
                    }
                },
                "400": {
                    "invalid_topic": {
                        "summary": "Invalid topic provided",
                        "description": "Topic is too short or contains inappropriate content",
                        "value": {
                            "error": "Validation Error",
                            "message": "Topic must be between 10 and 500 characters",
                            "error_code": "VALIDATION_ERROR",
                            "details": {
                                "field": "topic",
                                "issue": "too_short",
                                "min_length": 10,
                                "current_length": 5
                            }
                        }
                    }
                },
                "402": {
                    "quota_exceeded": {
                        "summary": "Content generation quota exceeded",
                        "description": "User has reached their monthly content generation limit",
                        "value": {
                            "error": "Quota Exceeded",
                            "message": "You have reached your monthly content generation limit of 50 posts",
                            "error_code": "QUOTA_EXCEEDED",
                            "details": {
                                "current_usage": 50,
                                "limit": 50,
                                "reset_date": "2024-02-01T00:00:00Z",
                                "upgrade_url": "https://app.techleadautopilot.com/upgrade"
                            }
                        }
                    }
                }
            }
        
        elif method == "get" and path.endswith("/content"):
            # List content responses
            examples["responses"] = {
                "200": {
                    "content_list": {
                        "summary": "List of user's content",
                        "description": "Paginated list of generated content with metadata",
                        "value": {
                            "content": [
                                {
                                    "id": "550e8400-e29b-41d4-a716-446655440000",
                                    "topic": "Leadership in Tech: Building High-Performance Teams",
                                    "content_type": "thought_leadership",
                                    "status": "published",
                                    "created_at": "2024-01-15T10:30:00Z",
                                    "published_at": "2024-01-16T06:30:00Z",
                                    "engagement": {
                                        "likes": 143,
                                        "comments": 28,
                                        "shares": 12,
                                        "consultations_generated": 2
                                    }
                                },
                                {
                                    "id": "660e8400-e29b-41d4-a716-446655440001",
                                    "topic": "The Future of AI in Software Development", 
                                    "content_type": "technical_deep_dive",
                                    "status": "scheduled",
                                    "created_at": "2024-01-14T14:20:00Z",
                                    "scheduled_for": "2024-01-18T06:30:00Z",
                                    "engagement_prediction": {
                                        "likes": 89,
                                        "comments": 15,
                                        "consultation_probability": 0.65
                                    }
                                }
                            ],
                            "pagination": {
                                "total": 47,
                                "page": 1,
                                "page_size": 20,
                                "total_pages": 3,
                                "has_next": True,
                                "next_page": 2
                            },
                            "filters_applied": {
                                "status": "all",
                                "content_type": "all",
                                "date_range": "last_30_days"
                            }
                        }
                    }
                }
            }
        
        return examples
    
    def _generate_lead_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for lead-related endpoints."""
        examples = {"request": {}, "responses": {}}
        
        if method == "get" and path.endswith("/leads"):
            examples["responses"] = {
                "200": {
                    "leads_list": {
                        "summary": "List of detected leads",
                        "description": "Prioritized list of consultation opportunities with scoring",
                        "value": {
                            "leads": [
                                {
                                    "id": "lead_123456789",
                                    "content_id": "550e8400-e29b-41d4-a716-446655440000",
                                    "inquiry_type": "consultation_request",
                                    "author_info": {
                                        "name": "Sarah Johnson",
                                        "title": "VP of Engineering",
                                        "company": "TechCorp Inc.",
                                        "company_size": "500-1000",
                                        "linkedin_profile": "https://linkedin.com/in/sarahjohnson"
                                    },
                                    "inquiry_content": "We're struggling with scaling our development team. Could use some guidance on best practices for growing from 15 to 50 engineers.",
                                    "score": {
                                        "total": 8.7,
                                        "breakdown": {
                                            "urgency": 9.2,
                                            "company_fit": 8.5,
                                            "seniority": 9.0,
                                            "engagement_quality": 8.1
                                        },
                                        "confidence": 0.87
                                    },
                                    "business_value": {
                                        "estimated_project_value": "€25,000 - €75,000",
                                        "confidence": 0.73,
                                        "factors": [
                                            "Large company size",
                                            "Senior decision maker",
                                            "Clear immediate need",
                                            "Technical leadership focus"
                                        ]
                                    },
                                    "priority": "high",
                                    "detected_at": "2024-01-16T08:45:00Z",
                                    "status": "new",
                                    "follow_up_suggestions": [
                                        "Send personal message within 2 hours",
                                        "Share relevant case study about scaling teams",
                                        "Offer 30-minute consultation call"
                                    ]
                                },
                                {
                                    "id": "lead_123456790",
                                    "content_id": "660e8400-e29b-41d4-a716-446655440001",
                                    "inquiry_type": "technical_question",
                                    "author_info": {
                                        "name": "Mike Chen",
                                        "title": "CTO",
                                        "company": "StartupXYZ",
                                        "company_size": "50-100",
                                        "linkedin_profile": "https://linkedin.com/in/mikechen"
                                    },
                                    "inquiry_content": "Interesting perspective on AI in development. We're evaluating ML tools for our code review process. Any recommendations?",
                                    "score": {
                                        "total": 6.8,
                                        "breakdown": {
                                            "urgency": 5.5,
                                            "company_fit": 7.2,
                                            "seniority": 8.8,
                                            "engagement_quality": 6.1
                                        },
                                        "confidence": 0.71
                                    },
                                    "business_value": {
                                        "estimated_project_value": "€10,000 - €35,000",
                                        "confidence": 0.65,
                                        "factors": [
                                            "Startup company size",
                                            "C-level decision maker",
                                            "Technical implementation focus"
                                        ]
                                    },
                                    "priority": "medium",
                                    "detected_at": "2024-01-16T10:15:00Z", 
                                    "status": "new"
                                }
                            ],
                            "summary": {
                                "total_leads": 23,
                                "new_leads": 8,
                                "high_priority": 3,
                                "medium_priority": 12,
                                "low_priority": 8,
                                "total_estimated_value": "€485,000 - €1,240,000",
                                "last_24h_leads": 5
                            },
                            "pagination": {
                                "total": 23,
                                "page": 1,
                                "page_size": 10,
                                "total_pages": 3
                            }
                        }
                    }
                }
            }
        
        return examples
    
    def _generate_analytics_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for analytics endpoints."""
        examples = {"request": {}, "responses": {}}
        
        if method == "get" and "analytics" in path:
            examples["responses"] = {
                "200": {
                    "analytics_overview": {
                        "summary": "Comprehensive analytics overview",
                        "description": "30-day analytics with content performance and lead attribution",
                        "value": {
                            "period": {
                                "start_date": "2023-12-16",
                                "end_date": "2024-01-15",
                                "days": 30
                            },
                            "content_performance": {
                                "total_posts": 12,
                                "total_engagement": {
                                    "likes": 1847,
                                    "comments": 342,
                                    "shares": 156,
                                    "views": 18420
                                },
                                "average_engagement": {
                                    "likes_per_post": 153.9,
                                    "comments_per_post": 28.5,
                                    "shares_per_post": 13.0,
                                    "engagement_rate": "7.2%"
                                },
                                "top_performing_content": [
                                    {
                                        "id": "550e8400-e29b-41d4-a716-446655440000",
                                        "topic": "Leadership in Tech: Building High-Performance Teams",
                                        "engagement_score": 9.1,
                                        "consultations_generated": 3
                                    }
                                ]
                            },
                            "lead_generation": {
                                "total_leads": 47,
                                "qualified_leads": 23,
                                "consultation_requests": 8,
                                "conversion_metrics": {
                                    "content_to_lead_rate": "3.9%",
                                    "lead_to_consultation_rate": "17.0%",
                                    "consultation_to_client_rate": "37.5%"
                                }
                            },
                            "business_impact": {
                                "consultation_pipeline_value": "€145,000 - €380,000",
                                "closed_deals_value": "€42,000",
                                "roi": {
                                    "investment": "€297", 
                                    "return": "€42,000",
                                    "roi_percentage": "14,141%"
                                }
                            },
                            "optimal_timing": {
                                "best_posting_days": ["tuesday", "thursday"],
                                "best_posting_time": "06:30 PST",
                                "peak_engagement_hours": [
                                    {"hour": "06:00-07:00", "engagement_multiplier": 1.8},
                                    {"hour": "17:00-18:00", "engagement_multiplier": 1.4}
                                ]
                            }
                        }
                    }
                }
            }
        
        return examples
    
    def _generate_auth_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for authentication endpoints."""
        examples = {"request": {}, "responses": {}}
        
        if method == "post" and "login" in path:
            examples["request"] = {
                "standard_login": {
                    "summary": "Standard login with email and password",
                    "value": {
                        "email": "user@example.com",
                        "password": "SecurePassword123!",
                        "remember_me": False
                    }
                },
                "trusted_device_login": {
                    "summary": "Login with extended session",
                    "value": {
                        "email": "user@example.com", 
                        "password": "SecurePassword123!",
                        "remember_me": True
                    }
                }
            }
            
            examples["responses"] = {
                "200": {
                    "successful_login": {
                        "summary": "Successful authentication",
                        "value": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 86400,
                            "refresh_token": "def502000a2b3c4d5e6f...",
                            "scope": "content:read content:write leads:read analytics:read",
                            "user": {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "email": "user@example.com",
                                "name": "John Doe",
                                "subscription_tier": "pro",
                                "organization": {
                                    "id": "org_123456789",
                                    "name": "TechCorp Consulting"
                                }
                            }
                        }
                    }
                },
                "401": {
                    "invalid_credentials": {
                        "summary": "Invalid login credentials",
                        "value": {
                            "error": "authentication_failed",
                            "error_description": "Invalid email or password",
                            "error_code": "AUTH_INVALID_CREDENTIALS"
                        }
                    }
                }
            }
        
        return examples
    
    def _generate_scheduler_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate examples for scheduler endpoints."""
        examples = {"request": {}, "responses": {}}
        
        if method == "post" and "schedule" in path:
            examples["request"] = {
                "standard_scheduling": {
                    "summary": "Schedule content with default settings",
                    "value": {
                        "max_posts_per_week": 3
                    }
                },
                "aggressive_scheduling": {
                    "summary": "More frequent posting schedule",
                    "value": {
                        "max_posts_per_week": 5
                    }
                }
            }
            
            examples["responses"] = {
                "200": {
                    "successful_scheduling": {
                        "summary": "Content successfully scheduled",
                        "value": {
                            "scheduled_posts": 3,
                            "scheduling_results": [
                                {
                                    "content_id": "550e8400-e29b-41d4-a716-446655440000",
                                    "scheduled_for": "2024-01-16T06:30:00Z",
                                    "platform": "linkedin",
                                    "optimal_time": True,
                                    "expected_engagement": 8.7
                                }
                            ],
                            "next_posting_times": {
                                "tuesday": {
                                    "time": "06:30:00",
                                    "timezone": "PST",
                                    "engagement_score": 0.89
                                },
                                "thursday": {
                                    "time": "06:30:00", 
                                    "timezone": "PST",
                                    "engagement_score": 0.85
                                }
                            },
                            "weekly_posting_strategy": "Quality-focused posting with proven optimal timing"
                        }
                    }
                }
            }
        
        return examples
    
    def _generate_generic_examples(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generic examples for unspecified endpoints."""
        examples = {"request": {}, "responses": {}}
        
        # Basic success response
        examples["responses"] = {
            "200": {
                "success": {
                    "summary": "Successful response",
                    "value": {
                        "success": True,
                        "message": "Operation completed successfully"
                    }
                }
            }
        }
        
        return examples