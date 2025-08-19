#!/usr/bin/env python3
"""
Quick Start LinkedIn Posting Script
Launch LinkedIn posting interface with immediate Monday post ready
"""

import sys
import os
from pathlib import Path

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'business_development'))

from linkedin_poster import LinkedInPosterInterface

def main():
    """Quick start LinkedIn posting with Monday post preview"""
    poster = LinkedInPosterInterface()
    
    print("🚀 WEEK 3 LINKEDIN POSTING - QUICK START")
    print("="*60)
    print("IMMEDIATE ACTION PLAN:")
    print("1. Post Monday's '10x Engineering Team' content NOW")
    print("2. Track engagement and consultation inquiries") 
    print("3. Follow up on high-priority leads within 24 hours")
    print("="*60)
    print()
    
    # Show Monday post preview immediately
    monday_post_id = "2025-01-20-monday-10x-teams"
    print("📝 MONDAY POST READY FOR IMMEDIATE POSTING:")
    poster.display_post_preview(monday_post_id)
    
    print("🎯 BUSINESS DEVELOPMENT TARGETS:")
    print("• Expected engagement: 8.0% (vs industry 2-3%)")
    print("• Target consultation inquiries: 2-3 team building requests")
    print("• Pipeline value target: $50K-$75K from this post")
    print()
    
    print("📋 POST-PUBLISHING CHECKLIST:")
    print("☐ Copy content above and post to LinkedIn at 7:00 AM")
    print("☐ Monitor comments for consultation signals")
    print("☐ Track metrics after 2 hours, 24 hours")
    print("☐ Respond to consultation inquiries within 2 hours")
    print("☐ Update metrics in system using option 4")
    print()
    
    # Ask if user wants to mark as published
    response = input("Ready to mark Monday post as published? (y/N): ").lower().strip()
    if response == 'y':
        poster.mark_post_as_published(monday_post_id)
        print("✅ Monday post marked as published!")
        print("📊 Use 'Update post metrics' when you have engagement data")
    
    # Launch full interface
    print("\n🔄 Launching full LinkedIn posting interface...")
    poster.interactive_menu()

if __name__ == "__main__":
    main()