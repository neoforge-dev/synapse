"""Deprecation management with automatic warnings and migration assistance."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class DeprecationLevel(str, Enum):
    """Level of deprecation severity."""
    INFO = "info"           # Informational notice
    WARNING = "warning"     # Deprecation warning
    CRITICAL = "critical"   # Critical - removal imminent
    SUNSET = "sunset"       # Feature removed


@dataclass
class DeprecationWarning:
    """Represents a deprecation warning."""
    feature: str
    level: DeprecationLevel
    message: str
    deprecated_since: datetime
    sunset_date: Optional[datetime] = None
    replacement: Optional[str] = None
    migration_guide: Optional[str] = None
    breaking_change: bool = False
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Get days until feature is sunset."""
        if not self.sunset_date:
            return None
        delta = self.sunset_date - datetime.now(timezone.utc)
        return max(0, delta.days)
    
    @property
    def is_urgent(self) -> bool:
        """Check if deprecation is urgent (less than 30 days)."""
        days = self.days_until_sunset
        return days is not None and days < 30


class DeprecationManager:
    """Manages API deprecations, warnings, and migration assistance.
    
    Provides:
    - Automatic deprecation warnings in API responses
    - Migration guidance and tooling
    - Sunset timeline management
    - Breaking change notifications
    - Client notification system
    """
    
    def __init__(self, base_docs_url: str = "https://docs.techleadautopilot.com"):
        """Initialize deprecation manager.
        
        Args:
            base_docs_url: Base URL for documentation links
        """
        self.base_docs_url = base_docs_url
        self.deprecations: Dict[str, DeprecationWarning] = {}
        self.endpoint_deprecations: Dict[str, List[str]] = {}  # endpoint -> deprecation keys
        self.client_notifications: Dict[str, List[str]] = {}   # client_id -> sent warnings
        
        # Initialize default deprecations
        self._setup_default_deprecations()
    
    def _setup_default_deprecations(self) -> None:
        """Set up default deprecation warnings."""
        now = datetime.now(timezone.utc)
        
        # Example deprecations for demonstration
        old_analytics = DeprecationWarning(
            feature="analytics_v1",
            level=DeprecationLevel.WARNING,
            message="The v1 analytics endpoint is deprecated. Use v2 for enhanced features.",
            deprecated_since=now,
            sunset_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
            replacement="/api/v2/analytics",
            migration_guide=urljoin(self.base_docs_url, "/migration/analytics-v1-to-v2"),
            breaking_change=False
        )
        
        old_content_format = DeprecationWarning(
            feature="content_response_format_v1",
            level=DeprecationLevel.CRITICAL,
            message="The v1 content response format will change in v2. Update your client code.",
            deprecated_since=now,
            sunset_date=datetime(2024, 11, 30, tzinfo=timezone.utc),
            replacement="v2 content response format",
            migration_guide=urljoin(self.base_docs_url, "/migration/content-format-v2"),
            breaking_change=True
        )
        
        self.register_deprecation("analytics_v1", old_analytics)
        self.register_deprecation("content_response_format_v1", old_content_format)
        
        # Map to endpoints
        self.endpoint_deprecations["/api/v1/analytics"] = ["analytics_v1"]
        self.endpoint_deprecations["/api/v1/content"] = ["content_response_format_v1"]
    
    def register_deprecation(self, key: str, deprecation: DeprecationWarning) -> None:
        """Register a new deprecation warning.
        
        Args:
            key: Unique key for the deprecation
            deprecation: Deprecation warning information
        """
        self.deprecations[key] = deprecation
        logger.info(f"Registered deprecation: {key} ({deprecation.level})")
    
    def add_endpoint_deprecation(self, endpoint: str, deprecation_key: str) -> None:
        """Associate a deprecation with an endpoint.
        
        Args:
            endpoint: API endpoint path
            deprecation_key: Key of registered deprecation
        """
        if deprecation_key not in self.deprecations:
            logger.error(f"Deprecation key {deprecation_key} not found")
            return
        
        if endpoint not in self.endpoint_deprecations:
            self.endpoint_deprecations[endpoint] = []
        
        if deprecation_key not in self.endpoint_deprecations[endpoint]:
            self.endpoint_deprecations[endpoint].append(deprecation_key)
    
    def get_deprecations_for_endpoint(self, endpoint: str) -> List[DeprecationWarning]:
        """Get deprecation warnings for specific endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            List of applicable deprecation warnings
        """
        deprecation_keys = self.endpoint_deprecations.get(endpoint, [])
        return [
            self.deprecations[key] for key in deprecation_keys
            if key in self.deprecations
        ]
    
    def get_deprecations_for_version(self, version: str) -> List[DeprecationWarning]:
        """Get deprecation warnings for specific API version.
        
        Args:
            version: API version (e.g., 'v1')
            
        Returns:
            List of deprecation warnings for the version
        """
        warnings = []
        
        for endpoint, deprecation_keys in self.endpoint_deprecations.items():
            if f"/{version}/" in endpoint or endpoint.endswith(f"/{version}"):
                for key in deprecation_keys:
                    if key in self.deprecations:
                        warnings.append(self.deprecations[key])
        
        return warnings
    
    def generate_deprecation_headers(
        self, 
        endpoint: str, 
        version: str,
        client_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate HTTP headers for deprecation warnings.
        
        Args:
            endpoint: API endpoint being accessed
            version: API version being used
            client_id: Optional client identifier for tracking
            
        Returns:
            Dictionary of HTTP headers to add to response
        """
        headers = {}
        
        # Get deprecations for this endpoint and version
        endpoint_deprecations = self.get_deprecations_for_endpoint(endpoint)
        version_deprecations = self.get_deprecations_for_version(version)
        
        all_deprecations = list(set(endpoint_deprecations + version_deprecations))
        
        if not all_deprecations:
            return headers
        
        # Find highest severity deprecation
        most_severe = max(all_deprecations, key=lambda d: self._severity_score(d.level))
        
        # Standard deprecation headers
        headers["Deprecation"] = "true"
        headers["Sunset"] = most_severe.sunset_date.isoformat() if most_severe.sunset_date else ""
        headers["Link"] = f'<{most_severe.migration_guide}>; rel="deprecation"' if most_severe.migration_guide else ""
        
        # Custom headers with detailed information
        headers["X-API-Deprecated"] = "true"
        headers["X-API-Deprecation-Level"] = most_severe.level.value
        headers["X-API-Deprecation-Message"] = most_severe.message
        
        if most_severe.replacement:
            headers["X-API-Replacement"] = most_severe.replacement
        
        if most_severe.days_until_sunset:
            headers["X-API-Days-Until-Sunset"] = str(most_severe.days_until_sunset)
        
        # Track notification for client
        if client_id:
            self._track_client_notification(client_id, most_severe.feature)
        
        return headers
    
    def _severity_score(self, level: DeprecationLevel) -> int:
        """Get numeric severity score for deprecation level.
        
        Args:
            level: Deprecation level
            
        Returns:
            Numeric score (higher = more severe)
        """
        scores = {
            DeprecationLevel.INFO: 1,
            DeprecationLevel.WARNING: 2,
            DeprecationLevel.CRITICAL: 3,
            DeprecationLevel.SUNSET: 4
        }
        return scores.get(level, 0)
    
    def _track_client_notification(self, client_id: str, feature: str) -> None:
        """Track that a client has been notified about a deprecation.
        
        Args:
            client_id: Client identifier
            feature: Deprecated feature name
        """
        if client_id not in self.client_notifications:
            self.client_notifications[client_id] = []
        
        if feature not in self.client_notifications[client_id]:
            self.client_notifications[client_id].append(feature)
            logger.info(f"Notified client {client_id} about deprecation: {feature}")
    
    def generate_response_warnings(
        self, 
        endpoint: str, 
        version: str
    ) -> List[Dict[str, Any]]:
        """Generate deprecation warnings for API response body.
        
        Args:
            endpoint: API endpoint being accessed
            version: API version being used
            
        Returns:
            List of warning objects to include in response
        """
        endpoint_deprecations = self.get_deprecations_for_endpoint(endpoint)
        version_deprecations = self.get_deprecations_for_version(version)
        
        all_deprecations = list(set(endpoint_deprecations + version_deprecations))
        
        warnings = []
        for deprecation in all_deprecations:
            warning = {
                "type": "deprecation",
                "level": deprecation.level.value,
                "feature": deprecation.feature,
                "message": deprecation.message,
                "deprecated_since": deprecation.deprecated_since.isoformat(),
                "breaking_change": deprecation.breaking_change
            }
            
            if deprecation.sunset_date:
                warning["sunset_date"] = deprecation.sunset_date.isoformat()
                warning["days_until_sunset"] = deprecation.days_until_sunset
            
            if deprecation.replacement:
                warning["replacement"] = deprecation.replacement
            
            if deprecation.migration_guide:
                warning["migration_guide"] = deprecation.migration_guide
            
            warnings.append(warning)
        
        return sorted(warnings, key=lambda w: self._severity_score(DeprecationLevel(w["level"])), reverse=True)
    
    def get_migration_assistance(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """Get migration assistance for version upgrade.
        
        Args:
            from_version: Current version
            to_version: Target version
            
        Returns:
            Migration assistance information
        """
        assistance = {
            "from_version": from_version,
            "to_version": to_version,
            "migration_steps": [],
            "breaking_changes": [],
            "automated_tools": [],
            "documentation_links": []
        }
        
        # Get all deprecations for the current version
        current_deprecations = self.get_deprecations_for_version(from_version)
        
        for deprecation in current_deprecations:
            if deprecation.breaking_change:
                assistance["breaking_changes"].append({
                    "feature": deprecation.feature,
                    "description": deprecation.message,
                    "replacement": deprecation.replacement,
                    "migration_guide": deprecation.migration_guide
                })
            
            if deprecation.migration_guide:
                assistance["documentation_links"].append({
                    "title": f"Migration guide for {deprecation.feature}",
                    "url": deprecation.migration_guide
                })
        
        # Add general migration steps
        assistance["migration_steps"].extend([
            "1. Review breaking changes and deprecation warnings",
            "2. Update client code to use new API endpoints",
            "3. Test thoroughly in staging environment",
            "4. Update API version in requests",
            "5. Monitor for any remaining warnings"
        ])
        
        # Add automated migration tools
        assistance["automated_tools"].extend([
            {
                "name": "API Migration Checker",
                "description": "Validate your requests against the new API version",
                "endpoint": f"/api/migration-tools/validate/{to_version}"
            },
            {
                "name": "Response Format Converter",
                "description": "Convert responses between API versions",
                "endpoint": f"/api/migration-tools/convert/{from_version}/{to_version}"
            }
        ])
        
        return assistance
    
    def get_urgent_deprecations(self) -> List[DeprecationWarning]:
        """Get list of urgent deprecations (sunset within 30 days).
        
        Returns:
            List of urgent deprecation warnings
        """
        return [
            deprecation for deprecation in self.deprecations.values()
            if deprecation.is_urgent
        ]
    
    def cleanup_expired_deprecations(self) -> int:
        """Remove deprecations that have passed their sunset date.
        
        Returns:
            Number of deprecations cleaned up
        """
        now = datetime.now(timezone.utc)
        expired_keys = []
        
        for key, deprecation in self.deprecations.items():
            if deprecation.sunset_date and now > deprecation.sunset_date:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.deprecations[key]
            # Remove from endpoint mappings
            for endpoint, keys in list(self.endpoint_deprecations.items()):
                if key in keys:
                    keys.remove(key)
                    if not keys:
                        del self.endpoint_deprecations[endpoint]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired deprecations")
        
        return len(expired_keys)
    
    def get_deprecation_stats(self) -> Dict[str, Any]:
        """Get statistics about current deprecations.
        
        Returns:
            Dictionary with deprecation statistics
        """
        stats = {
            "total_deprecations": len(self.deprecations),
            "by_level": {level.value: 0 for level in DeprecationLevel},
            "urgent_deprecations": len(self.get_urgent_deprecations()),
            "breaking_changes": 0,
            "affected_endpoints": len(self.endpoint_deprecations),
            "notified_clients": len(self.client_notifications)
        }
        
        for deprecation in self.deprecations.values():
            stats["by_level"][deprecation.level.value] += 1
            if deprecation.breaking_change:
                stats["breaking_changes"] += 1
        
        return stats