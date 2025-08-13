"""Metadata enhancement for better document organization."""

import logging
from typing import Dict, Any, List

from .auto_tagger import AutoTagger

logger = logging.getLogger(__name__)


class MetadataEnhancer:
    """Enhance document metadata with organizational information."""
    
    def __init__(self):
        self.auto_tagger = AutoTagger()
        logger.info("MetadataEnhancer initialized")
    
    def enhance_metadata(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance document metadata with tags, categories, and topics."""
        enhanced = document_data.copy()
        
        content = document_data.get("content", "")
        title = document_data.get("title", "")
        
        # Combine title and content for analysis
        analysis_text = f"{title} {content}".strip()
        
        if analysis_text:
            # Extract tags
            tags = self.auto_tagger.extract_tags(analysis_text, normalize=True)
            enhanced["tags"] = tags
            
            # Classify category
            category = self.auto_tagger.classify_category(analysis_text)
            enhanced["category"] = category
            
            # Extract hierarchical topics
            hierarchical_tags = self.auto_tagger.extract_hierarchical_tags(analysis_text)
            topics = []
            for category_tags in hierarchical_tags.values():
                topics.extend(category_tags)
            enhanced["topics"] = list(set(topics))  # Remove duplicates
            
            # Add confidence scores for tags
            tags_with_confidence = self.auto_tagger.extract_tags_with_confidence(analysis_text)
            enhanced["tag_confidence"] = dict(tags_with_confidence)
            
            logger.debug(f"Enhanced metadata for document {document_data.get('id', 'unknown')}: "
                        f"{len(tags)} tags, category: {category}")
        else:
            # No content to analyze
            enhanced["tags"] = []
            enhanced["category"] = "general"
            enhanced["topics"] = []
            enhanced["tag_confidence"] = {}
        
        return enhanced
    
    def suggest_organization_improvements(self, document_data: Dict[str, Any]) -> List[str]:
        """Suggest improvements for document organization."""
        suggestions = []
        
        content = document_data.get("content", "")
        title = document_data.get("title", "")
        existing_tags = document_data.get("tags", [])
        
        if not title:
            suggestions.append("Consider adding a descriptive title")
        
        if len(content) > 1000 and not existing_tags:
            suggestions.append("Document is long but has no tags - consider adding relevant tags")
        
        if content and not existing_tags:
            auto_tags = self.auto_tagger.extract_tags(f"{title} {content}")
            if auto_tags:
                suggestions.append(f"Suggested tags: {', '.join(auto_tags[:5])}")
        
        category = self.auto_tagger.classify_category(f"{title} {content}")
        if category != "general":
            suggestions.append(f"This appears to be a {category} document")
        
        return suggestions