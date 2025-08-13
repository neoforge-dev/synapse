"""Advanced query builder for constructing complex Boolean queries."""

import logging
from typing import Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class QueryOperator(Enum):
    """Query operators for Boolean logic."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class FieldCondition:
    """Represents a condition on a specific field."""
    
    def __init__(self, field_name: str, builder: "AdvancedQueryBuilder"):
        self.field_name = field_name
        self.conditions = {}
        self.builder = builder
    
    def equals(self, value: str) -> "AdvancedQueryBuilder":
        """Field equals exact value."""
        self.conditions["equals"] = value
        return self._apply_and_return_builder()
    
    def contains(self, value: str) -> "AdvancedQueryBuilder":
        """Field contains substring."""
        self.conditions["contains"] = value
        return self._apply_and_return_builder()
    
    def starts_with(self, value: str) -> "AdvancedQueryBuilder":
        """Field starts with prefix."""
        self.conditions["starts_with"] = value
        return self._apply_and_return_builder()
    
    def exists(self) -> "AdvancedQueryBuilder":
        """Field exists and is not null."""
        self.conditions["exists"] = True
        return self._apply_and_return_builder()
    
    def in_list(self, values: List[str]) -> "AdvancedQueryBuilder":
        """Field value is in provided list."""
        self.conditions["in"] = values
        return self._apply_and_return_builder()
    
    def after(self, date: str) -> "AdvancedQueryBuilder":
        """Field date is after specified date."""
        self.conditions["after"] = date
        return self._apply_and_return_builder()
    
    def before(self, date: str) -> "AdvancedQueryBuilder":
        """Field date is before specified date."""
        self.conditions["before"] = date
        return self._apply_and_return_builder()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {self.field_name: self.conditions}
    
    def _apply_and_return_builder(self) -> "AdvancedQueryBuilder":
        """Apply this condition to the builder and return the builder."""
        field_name = self.field_name
        conditions = self.conditions
        
        # Merge conditions for the same field instead of overwriting
        if field_name in self.builder._current_query.field_filters:
            self.builder._current_query.field_filters[field_name].update(conditions)
        else:
            self.builder._current_query.field_filters[field_name] = conditions.copy()
        
        return self.builder


class AdvancedQuery:
    """Represents a complete advanced query with all conditions."""
    
    def __init__(self):
        self.field_filters = {}
        self.content_search = ""
        self.boolean_operations = []
        self.sort_by = None
        self.sort_order = "desc"
        self.limit = None
    
    def get_query_string(self) -> str:
        """Generate query string representation."""
        parts = []
        
        # Add field filters
        for field, conditions in self.field_filters.items():
            for op, value in conditions.items():
                if op == "equals":
                    parts.append(f"{field}:{value}")
                elif op == "contains":
                    parts.append(f"{field}:*{value}*")
                elif op == "exists":
                    parts.append(f"{field}:*")
        
        # Add content search
        if self.content_search:
            parts.append(f"content:({self.content_search})")
        
        # Join with boolean operations
        if self.boolean_operations:
            query_parts = []
            op_index = 0
            for i, part in enumerate(parts):
                query_parts.append(part)
                if op_index < len(self.boolean_operations):
                    query_parts.append(self.boolean_operations[op_index].value)
                    op_index += 1
            return " ".join(query_parts)
        
        return " AND ".join(parts) if parts else ""
    
    def get_field_filters(self) -> Dict[str, Any]:
        """Get field filters dictionary."""
        return self.field_filters
    
    def get_content_search(self) -> str:
        """Get content search string."""
        return self.content_search
    
    def validate(self) -> bool:
        """Validate query structure."""
        # Basic validation - has some conditions
        return bool(self.field_filters or self.content_search)


class AdvancedQueryBuilder:
    """Builder for constructing complex Boolean queries."""
    
    def __init__(self):
        self.reset()
        logger.info("AdvancedQueryBuilder initialized")
    
    def reset(self) -> "AdvancedQueryBuilder":
        """Reset builder for new query."""
        self._current_query = AdvancedQuery()
        self._pending_field_condition = None
        self._group_stack = []
        return self
    
    def field(self, field_name: str) -> FieldCondition:
        """Start building condition for specified field."""
        condition = FieldCondition(field_name, self)
        return condition
    
    def AND(self) -> "AdvancedQueryBuilder":
        """Add AND operator."""
        self._current_query.boolean_operations.append(QueryOperator.AND)
        return self
    
    def OR(self) -> "AdvancedQueryBuilder":
        """Add OR operator."""
        self._current_query.boolean_operations.append(QueryOperator.OR)
        return self
    
    def NOT(self) -> "AdvancedQueryBuilder":
        """Add NOT operator."""
        self._current_query.boolean_operations.append(QueryOperator.NOT)
        return self
    
    def group_start(self) -> "AdvancedQueryBuilder":
        """Start a grouped condition (parentheses)."""
        self._group_stack.append("(")
        return self
    
    def group_end(self) -> "AdvancedQueryBuilder":
        """End a grouped condition."""
        if self._group_stack:
            self._group_stack.pop()
        return self
    
    def content(self, search_text: str) -> "AdvancedQueryBuilder":
        """Add content search terms."""
        self._current_query.content_search = search_text
        return self
    
    def sort_by(self, field: str, order: str = "desc") -> "AdvancedQueryBuilder":
        """Set sorting criteria."""
        self._current_query.sort_by = field
        self._current_query.sort_order = order
        return self
    
    def limit(self, count: int) -> "AdvancedQueryBuilder":
        """Set result limit."""
        self._current_query.limit = count
        return self
    
    def build(self) -> AdvancedQuery:
        """Build and return the final query."""
        if not self._current_query.validate():
            logger.warning("Built query has no conditions")
        
        result = self._current_query
        self.reset()  # Reset for next use
        return result