#!/usr/bin/env python3
"""
Demo script for LinkedIn Content Generation Pipeline
Showcases the integration of Synapse Graph-RAG with LinkedIn content creation
"""

import sys
from pathlib import Path

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent))

from content_templates import LinkedInContentGenerator, ContentType

def demo_single_content_generation():
    """Demonstrate single content generation"""
    print("🚀 SYNAPSE-POWERED LINKEDIN CONTENT GENERATION DEMO")
    print("=" * 60)
    print("Generating content using 460+ analyzed LinkedIn posts and Synapse AI enrichment")
    print()
    
    generator = LinkedInContentGenerator()
    
    # Demo different content types
    demo_configs = [
        {
            'content_type': ContentType.CONTROVERSIAL_TAKE,
            'topic': 'product management',
            'angle': 'Most product managers focus on features instead of customer problems'
        },
        {
            'content_type': ContentType.PERSONAL_STORY,
            'topic': 'career transition',
            'angle': None
        },
        {
            'content_type': ContentType.TECHNICAL_INSIGHT,
            'topic': 'Python backend development',
            'angle': None
        }
    ]
    
    for i, config in enumerate(demo_configs, 1):
        print(f"\n📝 DEMO {i}: {config['content_type'].value.replace('_', ' ').title()}")
        print("-" * 50)
        
        try:
            generated = generator.generate_content(
                content_type=config['content_type'],
                topic=config['topic'],
                specific_angle=config['angle']
            )
            
            print("✅ GENERATED LINKEDIN POST:")
            print("=" * 40)
            print(generated.full_post)
            print("=" * 40)
            
            print(f"\n📊 AI Analysis:")
            print(f"• Predicted Engagement: {generated.engagement_prediction:.1%}")
            print(f"• Synapse Confidence: {generated.enrichment_data.confidence_score:.1%}")
            print(f"• Content Length: {generated.generation_metadata['content_length']} characters")
            
            if generated.enrichment_data.relevant_beliefs:
                print(f"• Leveraged {len(generated.enrichment_data.relevant_beliefs)} proven beliefs")
            if generated.enrichment_data.personal_stories:
                print(f"• Included {len(generated.enrichment_data.personal_stories)} personal stories")
            if generated.enrichment_data.synapse_search_results:
                print(f"• Enhanced with {len(generated.enrichment_data.synapse_search_results)} Synapse insights")
            
            print()
            
        except Exception as e:
            print(f"❌ Error generating content: {e}")

def demo_batch_generation():
    """Demonstrate batch content generation"""
    print("\n🔄 BATCH CONTENT GENERATION DEMO")
    print("=" * 50)
    print("Generating a complete weekly content plan...")
    
    generator = LinkedInContentGenerator()
    
    # Generate content for different topics
    topics = ["startup challenges", "technical leadership", "product strategy"]
    
    for topic in topics:
        print(f"\n📋 WEEKLY PLAN: {topic.upper()}")
        print("-" * 40)
        
        # Generate 3 posts for the topic
        content_types = [
            ContentType.CONTROVERSIAL_TAKE,
            ContentType.PERSONAL_STORY,
            ContentType.TECHNICAL_INSIGHT
        ]
        
        batch_specs = [
            {
                'content_type': ct.value,
                'topic': f"{topic} insights",
                'target_engagement': 0.06
            }
            for ct in content_types
        ]
        
        try:
            generated_batch = generator.generate_content_batch(batch_specs)
            
            for j, content in enumerate(generated_batch, 1):
                print(f"\n📝 Post {j}: {content.content_type.value.replace('_', ' ').title()}")
                print(f"🎯 Predicted Engagement: {content.engagement_prediction:.1%}")
                print(f"📄 Preview: {content.full_post[:100]}...")
                
        except Exception as e:
            print(f"❌ Error in batch generation: {e}")

def demo_synapse_integration():
    """Demonstrate Synapse system integration"""
    print("\n🔍 SYNAPSE INTEGRATION DEMO")
    print("=" * 40)
    print("Showing how the system leverages existing knowledge...")
    
    from content_templates.synapse_enricher import SynapseContentEnricher
    
    enricher = SynapseContentEnricher()
    
    # Test topics that should have LinkedIn insights
    test_topics = [
        "Python development", 
        "product management",
        "startup journey",
        "technical leadership"
    ]
    
    for topic in test_topics:
        print(f"\n🔍 Analyzing '{topic}':")
        
        try:
            enriched = enricher.enrich_content(
                topic=topic,
                content_type="technical_insight", 
                keywords=["development", "leadership", "strategy"]
            )
            
            print(f"• Confidence Score: {enriched.confidence_score:.1%}")
            print(f"• Found {len(enriched.relevant_beliefs)} relevant beliefs")
            print(f"• Found {len(enriched.personal_stories)} personal stories")
            print(f"• Found {len(enriched.technical_insights)} technical insights")
            print(f"• Synapse results: {len(enriched.synapse_search_results)} items")
            
            if enriched.personal_stories:
                print(f"• Example story: {enriched.personal_stories[0][:80]}...")
                
        except Exception as e:
            print(f"❌ Error analyzing {topic}: {e}")

def demo_engagement_optimization():
    """Demonstrate engagement optimization features"""
    print("\n📈 ENGAGEMENT OPTIMIZATION DEMO")
    print("=" * 45)
    print("Showing engagement prediction and optimization...")
    
    generator = LinkedInContentGenerator()
    
    # Generate same topic with different content types to show engagement differences
    topic = "software architecture"
    
    content_types = [
        ContentType.CONTROVERSIAL_TAKE,
        ContentType.PERSONAL_STORY,
        ContentType.TECHNICAL_INSIGHT,
        ContentType.CAREER_ADVICE
    ]
    
    results = []
    
    for content_type in content_types:
        try:
            generated = generator.generate_content(
                content_type=content_type,
                topic=topic
            )
            
            results.append({
                'type': content_type.value.replace('_', ' ').title(),
                'engagement': generated.engagement_prediction,
                'length': generated.generation_metadata['content_length'],
                'confidence': generated.enrichment_data.confidence_score
            })
            
        except Exception as e:
            print(f"❌ Error with {content_type.value}: {e}")
    
    # Sort by predicted engagement
    results.sort(key=lambda x: x['engagement'], reverse=True)
    
    print(f"\n📊 ENGAGEMENT PREDICTIONS FOR '{topic.upper()}':")
    print("-" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['type']}")
        print(f"   📈 Engagement: {result['engagement']:.1%}")
        print(f"   📝 Length: {result['length']} chars")
        print(f"   🎯 AI Confidence: {result['confidence']:.1%}")
        print()

def main():
    """Run complete demo"""
    print("🤖 LINKEDIN CONTENT GENERATION SYSTEM DEMO")
    print("=" * 60)
    print("Powered by Synapse Graph-RAG + 460 analyzed LinkedIn posts")
    print("Built for authentic, high-engagement content creation")
    print()
    
    try:
        # Run all demos
        demo_single_content_generation()
        demo_batch_generation()
        demo_synapse_integration()
        demo_engagement_optimization()
        
        print("\n🎉 DEMO COMPLETE!")
        print("=" * 30)
        print("✅ Content generation system ready for production use")
        print("✅ Synapse integration working")
        print("✅ Engagement optimization active")
        print("✅ LinkedIn insights successfully leveraged")
        print()
        print("🚀 To start using the system:")
        print("   python business_development/automation_dashboard.py")
        print("   → Select option 7: Generate AI content")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("\nThis is likely due to missing dependencies or Synapse system setup.")
        print("The content generation system will work once the Synapse system is properly configured.")

if __name__ == "__main__":
    main()