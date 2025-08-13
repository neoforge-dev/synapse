"""Query template system for reusable query patterns."""

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from .advanced_query_builder import AdvancedQueryBuilder, AdvancedQuery

logger = logging.getLogger(__name__)


class QueryTemplateManager:
    """Manages query templates for common search patterns."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else Path.cwd() / "query_templates.json"
        self.templates = self._load_templates()
        self.query_builder = AdvancedQueryBuilder()
        logger.info("QueryTemplateManager initialized")
    
    def save_template(self, template: Dict[str, Any]) -> str:
        """Save a query template."""
        template_name = template["name"]
        
        # Validate template structure
        if not self._validate_template(template):
            raise ValueError(f"Invalid template structure: {template_name}")
        
        self.templates[template_name] = template
        self._persist_templates()
        
        logger.info(f"Saved query template: {template_name}")
        return template_name
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a query template by name."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())
    
    def delete_template(self, name: str) -> bool:
        """Delete a query template."""
        if name in self.templates:
            del self.templates[name]
            self._persist_templates()
            logger.info(f"Deleted query template: {name}")
            return True
        return False
    
    def apply_template(self, name: str, parameters: Dict[str, str]) -> AdvancedQuery:
        """Apply a template with provided parameters to create a query."""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        
        # Validate parameters
        required_params = template.get("parameters", [])
        missing_params = [p for p in required_params if p not in parameters]
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Apply parameters to query pattern
        query_pattern = template["query_pattern"]
        applied_pattern = self._apply_parameters(query_pattern, parameters)
        
        # Build query using the applied pattern
        return self._build_query_from_pattern(applied_pattern)
    
    def get_default_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get default query templates for common use cases."""
        return {
            "technical_docs": {
                "name": "technical_docs",
                "description": "Find technical documentation with specific technology",
                "query_pattern": {
                    "field_filters": {
                        "category": {"equals": "technical"},
                        "tags": {"contains": "{technology}"}
                    },
                    "content_search": "{search_term}"
                },
                "parameters": ["technology", "search_term"]
            },
            "recent_content": {
                "name": "recent_content",
                "description": "Find recent content in specific category",
                "query_pattern": {
                    "field_filters": {
                        "category": {"equals": "{category}"},
                        "created_at": {"after": "{date}"}
                    },
                    "sort_by": "created_at",
                    "sort_order": "desc"
                },
                "parameters": ["category", "date"]
            },
            "tagged_content": {
                "name": "tagged_content",
                "description": "Find content with multiple specific tags",
                "query_pattern": {
                    "field_filters": {
                        "tags": {"contains": "{tag1}"}
                    },
                    "boolean_ops": ["AND"],
                    "additional_filters": {
                        "tags": {"contains": "{tag2}"}
                    }
                },
                "parameters": ["tag1", "tag2"]
            },
            "meeting_notes": {
                "name": "meeting_notes",
                "description": "Find meeting notes with action items",
                "query_pattern": {
                    "field_filters": {
                        "category": {"equals": "business"},
                        "tags": {"contains": "meeting"}
                    },
                    "content_search": "action items OR TODO OR follow-up"
                },
                "parameters": []
            }
        }
    
    def install_default_templates(self):
        """Install default templates if they don't exist."""
        defaults = self.get_default_templates()
        installed_count = 0
        
        for name, template in defaults.items():
            if name not in self.templates:
                self.save_template(template)
                installed_count += 1
        
        logger.info(f"Installed {installed_count} default templates")
        return installed_count
    
    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """Validate template structure."""
        required_fields = ["name", "description", "query_pattern"]
        return all(field in template for field in required_fields)
    
    def _apply_parameters(self, pattern: Dict[str, Any], parameters: Dict[str, str]) -> Dict[str, Any]:
        """Apply parameters to a query pattern."""
        pattern_str = json.dumps(pattern)
        
        # Replace parameter placeholders
        for param_name, param_value in parameters.items():
            placeholder = f"{{{param_name}}}"
            pattern_str = pattern_str.replace(placeholder, param_value)
        
        return json.loads(pattern_str)
    
    def _build_query_from_pattern(self, pattern: Dict[str, Any]) -> AdvancedQuery:
        """Build an AdvancedQuery from a pattern dictionary."""
        builder = self.query_builder.reset()
        
        # Apply field filters
        field_filters = pattern.get("field_filters", {})
        first_filter = True
        
        for field_name, conditions in field_filters.items():
            if not first_filter:
                # Add AND between multiple field filters by default
                builder.AND()
            
            field_condition = builder.field(field_name)
            
            for condition_type, value in conditions.items():
                if condition_type == "equals":
                    field_condition.equals(value)
                elif condition_type == "contains":
                    field_condition.contains(value)
                elif condition_type == "starts_with":
                    field_condition.starts_with(value)
                elif condition_type == "exists":
                    field_condition.exists()
                elif condition_type == "in":
                    field_condition.in_list(value)
                elif condition_type == "after":
                    field_condition.after(value)
                elif condition_type == "before":
                    field_condition.before(value)
            
            first_filter = False
        
        # Apply content search
        if "content_search" in pattern:
            builder.content(pattern["content_search"])
        
        # Apply sorting
        if "sort_by" in pattern:
            sort_order = pattern.get("sort_order", "desc")
            builder.sort_by(pattern["sort_by"], sort_order)
        
        # Apply limit
        if "limit" in pattern:
            builder.limit(pattern["limit"])
        
        return builder.build()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load templates from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Could not load templates: {e}")
        
        return {}
    
    def _persist_templates(self):
        """Persist templates to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.templates, f, indent=2)
        except IOError as e:
            logger.error(f"Could not persist templates: {e}")