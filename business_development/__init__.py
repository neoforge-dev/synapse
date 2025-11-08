"""
Business Development Automation System
Complete LinkedIn content strategy and consultation generation system
"""

from .automation_dashboard import AutomationDashboard
from .consultation_inquiry_detector import ConsultationInquiryDetector, InquiryPattern
from .linkedin_posting_system import (
    ConsultationInquiry,
    LinkedInBusinessDevelopmentEngine,
    LinkedInPost,
)

__all__ = [
    'ConsultationInquiryDetector',
    'InquiryPattern',
    'LinkedInBusinessDevelopmentEngine',
    'LinkedInPost',
    'ConsultationInquiry',
    'AutomationDashboard'
]
