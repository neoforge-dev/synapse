#!/usr/bin/env python3
"""
Simple CLI for LinkedIn Content Generation
Quick content generation without the full dashboard interface
"""

import argparse
import sys
from pathlib import Path

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent))

from content_templates import LinkedInContentGenerator, ContentType

def main():
    parser = argparse.ArgumentParser(description='Generate LinkedIn content using Synapse AI')
    parser.add_argument('topic', help='Content topic (e.g., "product management", "Python development")')
    parser.add_argument('--type', choices=[
        'controversial', 'story', 'technical', 'advice', 'product', 'startup'
    ], default='story', help='Content type (default: story)')
    parser.add_argument('--angle', help='Specific angle or controversial take')
    parser.add_argument('--save', action='store_true', help='Save to content pipeline database')
    parser.add_argument('--batch', type=int, help='Generate multiple posts (1-7)')
    
    args = parser.parse_args()
    
    # Map CLI types to ContentType enum
    type_mapping = {
        'controversial': ContentType.CONTROVERSIAL_TAKE,
        'story': ContentType.PERSONAL_STORY,
        'technical': ContentType.TECHNICAL_INSIGHT,
        'advice': ContentType.CAREER_ADVICE,
        'product': ContentType.PRODUCT_MANAGEMENT,
        'startup': ContentType.STARTUP_LESSONS
    }
    
    content_type = type_mapping[args.type]
    generator = LinkedInContentGenerator()
    
    print(f"🤖 Generating {content_type.value.replace('_', ' ')} content about '{args.topic}'")
    if args.angle:
        print(f"📐 Angle: {args.angle}")
    print("=" * 60)
    
    try:
        if args.batch:
            # Generate batch content
            print(f"🔄 Generating {args.batch} posts...")
            
            content_types = list(type_mapping.values())[:args.batch]
            batch_specs = [
                {
                    'content_type': ct.value,
                    'topic': f"{args.topic} - {ct.value.replace('_', ' ')}",
                    'target_engagement': 0.06
                }
                for ct in content_types
            ]
            
            generated_batch = generator.generate_content_batch(batch_specs)
            
            for i, content in enumerate(generated_batch, 1):
                print(f"\n📝 POST {i}: {content.content_type.value.replace('_', ' ').title()}")
                print("-" * 50)
                print(content.full_post)
                print(f"\n📊 Predicted Engagement: {content.engagement_prediction:.1%}")
                print("-" * 50)
        else:
            # Generate single content
            generated = generator.generate_content(
                content_type=content_type,
                topic=args.topic,
                specific_angle=args.angle
            )
            
            print("✅ GENERATED CONTENT:")
            print("-" * 30)
            print(generated.full_post)
            print("-" * 30)
            
            print(f"\n📊 Analysis:")
            print(f"• Type: {generated.content_type.value.replace('_', ' ').title()}")
            print(f"• Predicted Engagement: {generated.engagement_prediction:.1%}")
            print(f"• Synapse Confidence: {generated.enrichment_data.confidence_score:.1%}")
            print(f"• Length: {generated.generation_metadata['content_length']} characters")
            
            if generated.enrichment_data.relevant_beliefs:
                print(f"• Used {len(generated.enrichment_data.relevant_beliefs)} core beliefs")
            if generated.enrichment_data.personal_stories:
                print(f"• Included {len(generated.enrichment_data.personal_stories)} personal stories")
        
        if args.save:
            # Note: Would integrate with automation dashboard save functionality
            print(f"\n💾 Content would be saved to pipeline (integration with automation dashboard)")
            
    except Exception as e:
        print(f"❌ Error generating content: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()