"""Request/Response transformers for API version compatibility."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Callable, List
from dataclasses import dataclass
from copy import deepcopy

logger = logging.getLogger(__name__)


@dataclass
class TransformationRule:
    """Represents a data transformation rule."""
    field_path: str              # Dot-notation path to field (e.g., "user.profile.name")
    transformation_type: str     # Type of transformation (rename, restructure, convert, etc.)
    source_field: Optional[str] = None    # Source field for renames/moves
    target_field: Optional[str] = None    # Target field for renames/moves
    converter: Optional[Callable] = None  # Custom converter function
    default_value: Any = None             # Default value if field missing


class BaseTransformer(ABC):
    """Base class for API data transformers."""
    
    def __init__(self):
        """Initialize transformer with transformation rules."""
        self.rules: List[TransformationRule] = []
        self.setup_rules()
    
    @abstractmethod
    def setup_rules(self) -> None:
        """Set up transformation rules for this transformer."""
        pass
    
    def add_rule(self, rule: TransformationRule) -> None:
        """Add a transformation rule.
        
        Args:
            rule: Transformation rule to add
        """
        self.rules.append(rule)
    
    def get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation.
        
        Args:
            data: Source dictionary
            path: Dot-notation path (e.g., "user.profile.name")
            
        Returns:
            Value at path, or None if not found
        """
        try:
            value = data
            for key in path.split('.'):
                if isinstance(value, dict):
                    value = value[key]
                else:
                    return None
            return value
        except (KeyError, TypeError):
            return None
    
    def set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation.
        
        Args:
            data: Target dictionary
            path: Dot-notation path (e.g., "user.profile.name")
            value: Value to set
        """
        keys = path.split('.')
        current = data
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value
    
    def remove_nested_value(self, data: Dict[str, Any], path: str) -> None:
        """Remove nested value from dictionary using dot notation.
        
        Args:
            data: Target dictionary
            path: Dot-notation path to remove
        """
        keys = path.split('.')
        current = data
        
        try:
            # Navigate to parent of target key
            for key in keys[:-1]:
                current = current[key]
            
            # Remove the final key
            if keys[-1] in current:
                del current[keys[-1]]
        except (KeyError, TypeError):
            pass
    
    def apply_transformation_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all transformation rules to data.
        
        Args:
            data: Data to transform
            
        Returns:
            Transformed data
        """
        result = deepcopy(data)
        
        for rule in self.rules:
            try:
                if rule.transformation_type == "rename":
                    self._apply_rename_rule(result, rule)
                elif rule.transformation_type == "restructure":
                    self._apply_restructure_rule(result, rule)
                elif rule.transformation_type == "convert":
                    self._apply_convert_rule(result, rule)
                elif rule.transformation_type == "add":
                    self._apply_add_rule(result, rule)
                elif rule.transformation_type == "remove":
                    self._apply_remove_rule(result, rule)
                else:
                    logger.warning(f"Unknown transformation type: {rule.transformation_type}")
            except Exception as e:
                logger.error(f"Failed to apply transformation rule {rule.field_path}: {e}")
        
        return result
    
    def _apply_rename_rule(self, data: Dict[str, Any], rule: TransformationRule) -> None:
        """Apply rename transformation rule."""
        if rule.source_field and rule.target_field:
            value = self.get_nested_value(data, rule.source_field)
            if value is not None:
                self.set_nested_value(data, rule.target_field, value)
                self.remove_nested_value(data, rule.source_field)
    
    def _apply_restructure_rule(self, data: Dict[str, Any], rule: TransformationRule) -> None:
        """Apply restructure transformation rule."""
        if rule.source_field and rule.target_field:
            value = self.get_nested_value(data, rule.source_field)
            if value is not None:
                self.set_nested_value(data, rule.target_field, value)
    
    def _apply_convert_rule(self, data: Dict[str, Any], rule: TransformationRule) -> None:
        """Apply convert transformation rule."""
        value = self.get_nested_value(data, rule.field_path)
        if value is not None and rule.converter:
            converted_value = rule.converter(value)
            self.set_nested_value(data, rule.field_path, converted_value)
    
    def _apply_add_rule(self, data: Dict[str, Any], rule: TransformationRule) -> None:
        """Apply add transformation rule."""
        if rule.default_value is not None:
            current_value = self.get_nested_value(data, rule.field_path)
            if current_value is None:
                self.set_nested_value(data, rule.field_path, rule.default_value)
    
    def _apply_remove_rule(self, data: Dict[str, Any], rule: TransformationRule) -> None:
        """Apply remove transformation rule."""
        self.remove_nested_value(data, rule.field_path)


class ResponseTransformer(BaseTransformer):
    """Transforms API responses between versions."""
    
    def __init__(self, from_version: str, to_version: str):
        """Initialize response transformer.
        
        Args:
            from_version: Source API version
            to_version: Target API version
        """
        self.from_version = from_version
        self.to_version = to_version
        super().__init__()
    
    def setup_rules(self) -> None:
        """Set up transformation rules based on version pair."""
        if self.from_version == "v1" and self.to_version == "v2":
            self._setup_v1_to_v2_rules()
        elif self.from_version == "v2" and self.to_version == "v1":
            self._setup_v2_to_v1_rules()
        elif self.from_version == "v1" and self.to_version == "v1.1":
            self._setup_v1_to_v1_1_rules()
        elif self.from_version == "v1.1" and self.to_version == "v1":
            self._setup_v1_1_to_v1_rules()
    
    def _setup_v1_to_v2_rules(self) -> None:
        """Set up v1 to v2 transformation rules."""
        # Content generation response format changes
        self.add_rule(TransformationRule(
            field_path="content.generated_text",
            transformation_type="rename",
            source_field="content.generated_text",
            target_field="content.text"
        ))
        
        self.add_rule(TransformationRule(
            field_path="content.engagement_prediction",
            transformation_type="restructure",
            source_field="content.engagement_prediction",
            target_field="content.predictions.engagement"
        ))
        
        # Lead scoring format changes
        self.add_rule(TransformationRule(
            field_path="lead.score",
            transformation_type="restructure",
            source_field="lead.score",
            target_field="lead.scoring.total_score"
        ))
        
        self.add_rule(TransformationRule(
            field_path="lead.scoring.confidence",
            transformation_type="add",
            default_value=0.85
        ))
        
        # Add new fields with defaults
        self.add_rule(TransformationRule(
            field_path="metadata.api_version",
            transformation_type="add",
            default_value="v2"
        ))
    
    def _setup_v2_to_v1_rules(self) -> None:
        """Set up v2 to v1 transformation rules."""
        # Reverse of v1 to v2 transformations
        self.add_rule(TransformationRule(
            field_path="content.text",
            transformation_type="rename",
            source_field="content.text",
            target_field="content.generated_text"
        ))
        
        self.add_rule(TransformationRule(
            field_path="content.predictions.engagement",
            transformation_type="restructure",
            source_field="content.predictions.engagement",
            target_field="content.engagement_prediction"
        ))
        
        self.add_rule(TransformationRule(
            field_path="lead.scoring.total_score",
            transformation_type="restructure",
            source_field="lead.scoring.total_score",
            target_field="lead.score"
        ))
        
        # Remove v2-specific fields
        self.add_rule(TransformationRule(
            field_path="lead.scoring.confidence",
            transformation_type="remove"
        ))
        
        self.add_rule(TransformationRule(
            field_path="metadata.api_version",
            transformation_type="remove"
        ))
    
    def _setup_v1_to_v1_1_rules(self) -> None:
        """Set up v1 to v1.1 transformation rules."""
        # Add new optional fields
        self.add_rule(TransformationRule(
            field_path="content.optimization_suggestions",
            transformation_type="add",
            default_value=[]
        ))
        
        self.add_rule(TransformationRule(
            field_path="analytics.advanced_metrics",
            transformation_type="add",
            default_value={}
        ))
    
    def _setup_v1_1_to_v1_rules(self) -> None:
        """Set up v1.1 to v1 transformation rules."""
        # Remove v1.1-specific fields for backward compatibility
        self.add_rule(TransformationRule(
            field_path="content.optimization_suggestions",
            transformation_type="remove"
        ))
        
        self.add_rule(TransformationRule(
            field_path="analytics.advanced_metrics",
            transformation_type="remove"
        ))
    
    def transform(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform response data between versions.
        
        Args:
            response_data: Original response data
            
        Returns:
            Transformed response data
        """
        try:
            transformed = self.apply_transformation_rules(response_data)
            
            # Add transformation metadata
            if "metadata" not in transformed:
                transformed["metadata"] = {}
            
            transformed["metadata"]["transformed"] = True
            transformed["metadata"]["from_version"] = self.from_version
            transformed["metadata"]["to_version"] = self.to_version
            
            return transformed
            
        except Exception as e:
            logger.error(f"Response transformation failed ({self.from_version} -> {self.to_version}): {e}")
            # Return original data if transformation fails
            return response_data


class RequestTransformer(BaseTransformer):
    """Transforms API requests between versions."""
    
    def __init__(self, from_version: str, to_version: str):
        """Initialize request transformer.
        
        Args:
            from_version: Client API version
            to_version: Server API version
        """
        self.from_version = from_version
        self.to_version = to_version
        super().__init__()
    
    def setup_rules(self) -> None:
        """Set up transformation rules based on version pair."""
        if self.from_version == "v1" and self.to_version == "v2":
            self._setup_v1_to_v2_rules()
        elif self.from_version == "v2" and self.to_version == "v1":
            self._setup_v2_to_v1_rules()
    
    def _setup_v1_to_v2_rules(self) -> None:
        """Set up v1 to v2 request transformation rules."""
        # Content generation request changes
        self.add_rule(TransformationRule(
            field_path="content_type",
            transformation_type="convert",
            converter=lambda x: x.upper() if isinstance(x, str) else x
        ))
        
        # Add required fields for v2
        self.add_rule(TransformationRule(
            field_path="preferences.optimization_level",
            transformation_type="add",
            default_value="standard"
        ))
    
    def _setup_v2_to_v1_rules(self) -> None:
        """Set up v2 to v1 request transformation rules."""
        # Remove v2-specific fields
        self.add_rule(TransformationRule(
            field_path="preferences.optimization_level",
            transformation_type="remove"
        ))
        
        # Convert content_type back to v1 format
        self.add_rule(TransformationRule(
            field_path="content_type",
            transformation_type="convert",
            converter=lambda x: x.lower() if isinstance(x, str) else x
        ))
    
    def transform(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request data between versions.
        
        Args:
            request_data: Original request data
            
        Returns:
            Transformed request data
        """
        try:
            return self.apply_transformation_rules(request_data)
            
        except Exception as e:
            logger.error(f"Request transformation failed ({self.from_version} -> {self.to_version}): {e}")
            # Return original data if transformation fails
            return request_data


class TransformerRegistry:
    """Registry for managing data transformers."""
    
    def __init__(self):
        """Initialize transformer registry."""
        self._response_transformers: Dict[Tuple[str, str], Type[ResponseTransformer]] = {}
        self._request_transformers: Dict[Tuple[str, str], Type[RequestTransformer]] = {}
    
    def register_response_transformer(
        self, 
        from_version: str, 
        to_version: str, 
        transformer_class: Type[ResponseTransformer]
    ) -> None:
        """Register a response transformer.
        
        Args:
            from_version: Source version
            to_version: Target version
            transformer_class: Transformer class
        """
        key = (from_version, to_version)
        self._response_transformers[key] = transformer_class
    
    def register_request_transformer(
        self,
        from_version: str,
        to_version: str,
        transformer_class: Type[RequestTransformer]
    ) -> None:
        """Register a request transformer.
        
        Args:
            from_version: Source version
            to_version: Target version
            transformer_class: Transformer class
        """
        key = (from_version, to_version)
        self._request_transformers[key] = transformer_class
    
    def get_response_transformer(
        self, 
        from_version: str, 
        to_version: str
    ) -> Optional[ResponseTransformer]:
        """Get response transformer for version pair.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            Response transformer instance if available
        """
        key = (from_version, to_version)
        transformer_class = self._response_transformers.get(key, ResponseTransformer)
        
        try:
            return transformer_class(from_version, to_version)
        except Exception as e:
            logger.error(f"Failed to create response transformer: {e}")
            return None
    
    def get_request_transformer(
        self,
        from_version: str,
        to_version: str
    ) -> Optional[RequestTransformer]:
        """Get request transformer for version pair.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            Request transformer instance if available
        """
        key = (from_version, to_version)
        transformer_class = self._request_transformers.get(key, RequestTransformer)
        
        try:
            return transformer_class(from_version, to_version)
        except Exception as e:
            logger.error(f"Failed to create request transformer: {e}")
            return None
    
    def has_transformer(self, from_version: str, to_version: str, transformer_type: str = "response") -> bool:
        """Check if transformer exists for version pair.
        
        Args:
            from_version: Source version
            to_version: Target version
            transformer_type: Type of transformer ("response" or "request")
            
        Returns:
            Whether transformer exists
        """
        key = (from_version, to_version)
        
        if transformer_type == "response":
            return key in self._response_transformers or from_version != to_version
        elif transformer_type == "request":
            return key in self._request_transformers or from_version != to_version
        else:
            return False


# Global transformer registry
transformer_registry = TransformerRegistry()