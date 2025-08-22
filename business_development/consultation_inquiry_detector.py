#!/usr/bin/env python3
"""
Consultation Inquiry Detection and Follow-up System
Automatically detect consultation opportunities and manage systematic follow-up
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from linkedin_posting_system import ConsultationInquiry, LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class InquiryPattern:
    """Pattern for detecting consultation inquiries"""
    keywords: list[str]
    inquiry_type: str
    priority_boost: int
    estimated_value_base: int

class ConsultationInquiryDetector:
    """Detect consultation inquiries from various channels"""

    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.inquiry_patterns = self._load_inquiry_patterns()

    def _load_inquiry_patterns(self) -> list[InquiryPattern]:
        """Load patterns for detecting consultation inquiries"""
        return [
            # Team Building Consultation Patterns
            InquiryPattern(
                keywords=["team building", "team performance", "team velocity", "team culture", "10x team", "scaling team", "team problems"],
                inquiry_type="team_building",
                priority_boost=2,
                estimated_value_base=25000
            ),
            InquiryPattern(
                keywords=["hiring", "recruitment", "team scaling", "finding developers", "hiring strategy", "team growth", "recruiting"],
                inquiry_type="hiring_strategy",
                priority_boost=2,
                estimated_value_base=15000
            ),

            # Technical Architecture Consultation Patterns
            InquiryPattern(
                keywords=["architecture", "system design", "technical debt", "refactoring", "scalability", "performance"],
                inquiry_type="technical_architecture",
                priority_boost=3,
                estimated_value_base=40000
            ),
            InquiryPattern(
                keywords=["fractional cto", "part time cto", "interim cto", "technical advisor", "cto services", "technical leadership"],
                inquiry_type="fractional_cto",
                priority_boost=5,
                estimated_value_base=75000
            ),

            # #NOBUILD Philosophy Consultation Patterns
            InquiryPattern(
                keywords=["build vs buy", "nobuild", "technical decisions", "engineering costs", "saas vs custom", "technology audit"],
                inquiry_type="nobuild_audit",
                priority_boost=3,
                estimated_value_base=20000
            ),
            InquiryPattern(
                keywords=["over engineering", "premature optimization", "engineering efficiency", "development velocity", "technical strategy"],
                inquiry_type="engineering_efficiency",
                priority_boost=2,
                estimated_value_base=30000
            ),

            # General Consultation Patterns
            InquiryPattern(
                keywords=["consulting", "help", "advice", "discuss", "chat", "call", "meeting", "consultation"],
                inquiry_type="general_consultation",
                priority_boost=1,
                estimated_value_base=10000
            ),
            InquiryPattern(
                keywords=["startup", "early stage", "series a", "series b", "scaling", "growth"],
                inquiry_type="startup_scaling",
                priority_boost=2,
                estimated_value_base=35000
            )
        ]

    def analyze_text_for_consultation_signals(self, text: str, source_post_id: str) -> tuple[str, int, int] | None:
        """
        Analyze text for consultation inquiry signals
        Returns: (inquiry_type, priority_score, estimated_value) or None
        """
        text_lower = text.lower()

        # Strong consultation indicators
        strong_indicators = [
            r"\b(would love to|interested in|need help|looking for|want to discuss|can you help|seeking advice)\b",
            r"\b(schedule|book|call|meeting|consultation|discuss this|dive deeper)\b",
            r"\b(our company|our startup|our team|we are|we're struggling|we need)\b",
            r"\b(similar situation|same problem|facing this|dealing with|experiencing)\b"
        ]

        has_strong_indicator = any(re.search(pattern, text_lower) for pattern in strong_indicators)

        best_match = None
        highest_score = 0

        for pattern in self.inquiry_patterns:
            keyword_matches = sum(1 for keyword in pattern.keywords if keyword in text_lower)

            if keyword_matches > 0:
                # Calculate priority score
                base_score = keyword_matches
                if has_strong_indicator:
                    base_score += 3

                # Company size indicators boost priority
                company_indicators = ["startup", "series a", "series b", "funded", "employees", "team size"]
                if any(indicator in text_lower for indicator in company_indicators):
                    base_score += 1

                # Technical complexity indicators
                tech_indicators = ["complex", "scale", "enterprise", "production", "architecture"]
                if any(indicator in text_lower for indicator in tech_indicators):
                    base_score += 1

                final_score = base_score + pattern.priority_boost

                if final_score > highest_score:
                    highest_score = final_score
                    best_match = pattern

        if best_match and highest_score >= 3:  # Minimum threshold for consultation inquiry
            return (best_match.inquiry_type, min(highest_score, 5), best_match.estimated_value_base)

        return None

    def detect_company_size_from_text(self, text: str) -> str:
        """Extract company size from text content"""
        text_lower = text.lower()

        if any(term in text_lower for term in ["series c", "series d", "public", "enterprise", "fortune"]):
            return "Enterprise (500+ employees)"
        elif any(term in text_lower for term in ["series b", "scale up", "100", "200"]):
            return "Series B (50-200 employees)"
        elif any(term in text_lower for term in ["series a", "startup", "50", "team of"]):
            return "Series A (20-50 employees)"
        elif any(term in text_lower for term in ["seed", "early stage", "small team", "founder"]):
            return "Seed/Pre-Series A (5-20 employees)"
        else:
            return "Unknown"

    def process_linkedin_comment(self, post_id: str, comment_text: str, commenter_name: str, commenter_profile: str = "") -> str | None:
        """Process LinkedIn comment for consultation inquiry"""
        analysis = self.analyze_text_for_consultation_signals(comment_text, post_id)

        if analysis:
            inquiry_type, priority_score, estimated_value = analysis
            company_size = self.detect_company_size_from_text(comment_text + " " + commenter_profile)

            inquiry = ConsultationInquiry(
                inquiry_id=f"comment-{post_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                source_post_id=post_id,
                contact_name=commenter_name,
                company="Unknown",  # Would need profile analysis
                company_size=company_size,
                inquiry_type=inquiry_type,
                inquiry_channel="linkedin_comment",
                inquiry_text=comment_text,
                estimated_value=estimated_value,
                priority_score=priority_score,
                status="new",
                created_at=datetime.now().isoformat()
            )

            self.business_engine.log_consultation_inquiry(inquiry)
            logger.info(f"Detected consultation inquiry from comment: {inquiry.inquiry_id}")
            return inquiry.inquiry_id

        return None

    def process_linkedin_dm(self, post_id: str, dm_text: str, sender_name: str, sender_company: str = "") -> str | None:
        """Process LinkedIn DM for consultation inquiry"""
        analysis = self.analyze_text_for_consultation_signals(dm_text, post_id)

        if analysis:
            inquiry_type, priority_score, estimated_value = analysis
            company_size = self.detect_company_size_from_text(dm_text)

            # DMs get higher priority (more intentional)
            priority_score = min(priority_score + 1, 5)

            inquiry = ConsultationInquiry(
                inquiry_id=f"dm-{post_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                source_post_id=post_id,
                contact_name=sender_name,
                company=sender_company or "Unknown",
                company_size=company_size,
                inquiry_type=inquiry_type,
                inquiry_channel="linkedin_dm",
                inquiry_text=dm_text,
                estimated_value=int(estimated_value * 1.5),  # DMs typically higher value
                priority_score=priority_score,
                status="new",
                created_at=datetime.now().isoformat()
            )

            self.business_engine.log_consultation_inquiry(inquiry)
            logger.info(f"Detected consultation inquiry from DM: {inquiry.inquiry_id}")
            return inquiry.inquiry_id

        return None

    def generate_follow_up_response(self, inquiry_id: str) -> dict[str, str]:
        """Generate appropriate follow-up response for consultation inquiry"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM consultation_inquiries WHERE inquiry_id = ?', (inquiry_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "Inquiry not found"}

        columns = [description[0] for description in cursor.description]
        inquiry = dict(zip(columns, result, strict=False))
        conn.close()

        # Generate response based on inquiry type
        response_templates = {
            "team_building": {
                "comment_reply": "Thanks for the comment! Team velocity challenges are common when scaling. I've helped several companies go from inconsistent delivery to predictable sprint outcomes. Happy to share some specific approaches if you'd like to continue the conversation via DM.",
                "dm_response": f"Hi {inquiry['contact_name']}, thanks for reaching out about your team building challenges. I've worked with companies similar to yours to improve team velocity and culture. I typically start with a quick 15-minute assessment to understand your specific situation. Would you be interested in a brief call to discuss your team's current challenges and see if there's a fit for working together?"
            },
            "fractional_cto": {
                "comment_reply": "Appreciate the interest in fractional CTO services! I work with companies at various stages to provide strategic technical leadership without the full-time commitment. Feel free to DM me to discuss your specific technical leadership needs.",
                "dm_response": f"Hi {inquiry['contact_name']}, thanks for your interest in fractional CTO services. I'd love to learn more about your company's technical challenges and see how I can help. I typically start with a 30-minute strategic assessment call to understand your current tech stack, team, and business objectives. Would you be available for a brief call this week or next?"
            },
            "nobuild_audit": {
                "comment_reply": "Great question about build vs buy decisions! The #NOBUILD approach has saved companies significant engineering time and costs. I'd be happy to discuss how to apply this framework to your specific technology decisions - feel free to DM me.",
                "dm_response": f"Hi {inquiry['contact_name']}, thanks for reaching out about technology decision-making. The #NOBUILD audit process I've developed has helped companies save 40-60% on engineering costs by making smarter build vs buy decisions. I'd be happy to walk through a quick assessment of your current tech stack and identify potential optimization opportunities. Would you be interested in a 20-minute call to discuss your specific situation?"
            },
            "general_consultation": {
                "comment_reply": "Thanks for the comment! I'd be happy to discuss this further. Feel free to send me a DM and we can explore how to apply these concepts to your specific situation.",
                "dm_response": f"Hi {inquiry['contact_name']}, thanks for reaching out. I'd be happy to discuss your technical challenges in more detail. I typically start with a brief 15-20 minute call to understand your situation and see where I might be able to help. Would you be available for a quick call this week?"
            }
        }

        inquiry_type = inquiry.get('inquiry_type', 'general_consultation')
        template = response_templates.get(inquiry_type, response_templates['general_consultation'])

        # Add Calendly link for higher priority inquiries
        if inquiry.get('priority_score', 0) >= 4:
            template['dm_response'] += "\n\nIf you'd prefer, you can also book directly on my calendar: [Calendly link would go here]"

        return template

    def get_pending_inquiries(self, priority_threshold: int = 3) -> list[dict]:
        """Get pending consultation inquiries above priority threshold"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM consultation_inquiries 
            WHERE status = 'new' AND priority_score >= ?
            ORDER BY priority_score DESC, created_at ASC
        ''', (priority_threshold,))

        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        inquiries = []
        for result in results:
            inquiry = dict(zip(columns, result, strict=False))
            inquiries.append(inquiry)

        conn.close()
        return inquiries

    def mark_inquiry_contacted(self, inquiry_id: str, notes: str = ""):
        """Mark inquiry as contacted and add notes"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE consultation_inquiries 
            SET status = 'contacted', last_contact = ?, notes = ?
            WHERE inquiry_id = ?
        ''', (datetime.now().isoformat(), notes, inquiry_id))

        conn.commit()
        conn.close()
        logger.info(f"Marked inquiry as contacted: {inquiry_id}")

def main():
    """Demonstrate consultation inquiry detection system"""
    detector = ConsultationInquiryDetector()

    # Test comment processing
    sample_comments = [
        {
            "post_id": "2025-01-20-monday-10x-teams",
            "comment": "Great post! We're struggling with team velocity at our Series A startup. Our 15-person engineering team seems to be slowing down despite hiring more people. Would love to discuss your approach to team building.",
            "commenter": "Sarah Johnson"
        },
        {
            "post_id": "2025-01-21-tuesday-code-reviews",
            "comment": "This resonates! We've been looking for a fractional CTO to help us implement better engineering processes. Are you available for this type of work?",
            "commenter": "Mike Chen"
        },
        {
            "post_id": "2025-01-22-wednesday-hiring",
            "comment": "Interesting perspective on the #NOBUILD approach. Our startup has been building everything custom and burning through our engineering budget. Need help with a technology audit.",
            "commenter": "Alex Rivera"
        }
    ]

    print("🔍 Processing sample consultation inquiries...")

    for comment in sample_comments:
        inquiry_id = detector.process_linkedin_comment(
            comment["post_id"],
            comment["comment"],
            comment["commenter"]
        )

        if inquiry_id:
            print(f"✅ Detected inquiry: {inquiry_id}")

            # Generate follow-up response
            response = detector.generate_follow_up_response(inquiry_id)
            print(f"💬 Suggested response: {response.get('comment_reply', 'No response generated')}")
            print()

    # Get pending inquiries
    pending = detector.get_pending_inquiries()
    print(f"📋 Total pending inquiries: {len(pending)}")

    for inquiry in pending:
        print(f"- {inquiry['inquiry_type']} inquiry from {inquiry['contact_name']} (Priority: {inquiry['priority_score']}) - ${inquiry['estimated_value']:,}")

    # Calculate total pipeline value
    total_pipeline = sum(inquiry['estimated_value'] for inquiry in pending)
    print(f"\n💰 Total pending pipeline value: ${total_pipeline:,}")

    print("\n✅ Consultation Inquiry Detection System ready!")
    print("Ready to monitor LinkedIn engagement and automatically detect consultation opportunities.")

if __name__ == "__main__":
    main()
