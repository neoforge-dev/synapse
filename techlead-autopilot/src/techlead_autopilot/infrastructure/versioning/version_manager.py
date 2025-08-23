"""API version management with backward compatibility and routing support."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from packaging import version

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """Status of API version."""
    STABLE = "stable"
    BETA = "beta"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


class CompatibilityLevel(str, Enum):
    """Level of backward compatibility."""
    FULL = "full"           # 100% backward compatible
    PARTIAL = "partial"     # Some breaking changes with fallbacks
    BREAKING = "breaking"   # Significant breaking changes
    NONE = "none"          # No compatibility


@dataclass
class VersionInfo:
    """Information about an API version."""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    supported_features: Set[str] = None
    breaking_changes: List[str] = None
    
    def __post_init__(self):
        if self.supported_features is None:
            self.supported_features = set()
        if self.breaking_changes is None:
            self.breaking_changes = []
    
    @property
    def is_deprecated(self) -> bool:
        """Check if version is deprecated."""
        return self.status in (VersionStatus.DEPRECATED, VersionStatus.SUNSET)
    
    @property
    def is_active(self) -> bool:
        """Check if version is still active (not sunset)."""
        return self.status != VersionStatus.SUNSET
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Get days until version sunset."""
        if not self.sunset_date:
            return None
        delta = self.sunset_date - datetime.now(timezone.utc)
        return max(0, delta.days)


@dataclass
class VersionCompatibility:
    """Compatibility information between API versions."""
    from_version: str
    to_version: str
    compatibility_level: CompatibilityLevel
    breaking_changes: List[str]
    migration_guide_url: Optional[str] = None
    transformer_available: bool = False


class APIVersionManager:
    """Manages API versions, compatibility, and routing.
    
    Handles:
    - Version detection from requests
    - Backward compatibility checking
    - Breaking change tracking
    - Version lifecycle management
    - Automatic version routing
    """
    
    def __init__(self):
        """Initialize API version manager."""
        self.versions: Dict[str, VersionInfo] = {}
        self.compatibility_matrix: Dict[Tuple[str, str], VersionCompatibility] = {}
        self.default_version = "v1"
        self.supported_versions = set()
        
        # Initialize with default versions
        self._setup_default_versions()
    
    def _setup_default_versions(self) -> None:
        """Set up default API versions."""
        now = datetime.now(timezone.utc)
        
        # Version 1.0 - Current stable
        v1_info = VersionInfo(
            version="v1",
            status=VersionStatus.STABLE,
            release_date=now,
            supported_features={
                "content_generation", "lead_detection", "analytics", 
                "user_management", "organization_management"
            }
        )
        
        # Version 1.1 - Minor update with new features
        v1_1_info = VersionInfo(
            version="v1.1",
            status=VersionStatus.BETA,
            release_date=now,
            supported_features={
                "content_generation", "lead_detection", "analytics",
                "user_management", "organization_management",
                "advanced_analytics", "bulk_operations"
            }
        )
        
        # Version 2.0 - Major update (future)
        v2_info = VersionInfo(
            version="v2",
            status=VersionStatus.BETA,
            release_date=now,
            supported_features={
                "content_generation_v2", "ai_lead_scoring", "advanced_analytics",
                "user_management_v2", "organization_management", "integrations",
                "bulk_operations", "real_time_updates"
            },
            breaking_changes=[
                "Content generation response format changed",
                "Lead scoring algorithm updated",
                "Authentication flow modified"
            ]
        )
        
        self.register_version(v1_info)
        self.register_version(v1_1_info)
        self.register_version(v2_info)
        
        # Set up compatibility matrix
        self._setup_compatibility_matrix()
    
    def _setup_compatibility_matrix(self) -> None:
        """Set up compatibility relationships between versions."""
        # v1 to v1.1 - Full compatibility (minor version)
        v1_to_v1_1 = VersionCompatibility(
            from_version="v1",
            to_version="v1.1", 
            compatibility_level=CompatibilityLevel.FULL,
            breaking_changes=[],
            transformer_available=True
        )
        
        # v1.1 to v1 - Full backward compatibility
        v1_1_to_v1 = VersionCompatibility(
            from_version="v1.1",
            to_version="v1",
            compatibility_level=CompatibilityLevel.FULL,
            breaking_changes=[],
            transformer_available=True
        )
        
        # v1 to v2 - Partial compatibility (major version)
        v1_to_v2 = VersionCompatibility(
            from_version="v1",
            to_version="v2",
            compatibility_level=CompatibilityLevel.PARTIAL,
            breaking_changes=[
                "Content generation response format changed",
                "Lead scoring algorithm updated"
            ],
            migration_guide_url="https://docs.techleadautopilot.com/migration/v1-to-v2",
            transformer_available=True
        )
        
        # v2 to v1 - Breaking compatibility
        v2_to_v1 = VersionCompatibility(
            from_version="v2",
            to_version="v1",
            compatibility_level=CompatibilityLevel.BREAKING,
            breaking_changes=[
                "Advanced features not available in v1",
                "Response format incompatible"
            ],
            migration_guide_url="https://docs.techleadautopilot.com/migration/v2-to-v1",
            transformer_available=False
        )
        
        self.register_compatibility(v1_to_v1_1)
        self.register_compatibility(v1_1_to_v1)
        self.register_compatibility(v1_to_v2)
        self.register_compatibility(v2_to_v1)
    
    def register_version(self, version_info: VersionInfo) -> None:
        """Register a new API version.
        
        Args:
            version_info: Information about the version
        """
        self.versions[version_info.version] = version_info
        if version_info.is_active:
            self.supported_versions.add(version_info.version)
        
        logger.info(f"Registered API version {version_info.version} ({version_info.status})")
    
    def register_compatibility(self, compatibility: VersionCompatibility) -> None:
        """Register compatibility information between versions.
        
        Args:
            compatibility: Compatibility information
        """
        key = (compatibility.from_version, compatibility.to_version)
        self.compatibility_matrix[key] = compatibility
        
        logger.debug(
            f"Registered compatibility: {compatibility.from_version} -> "
            f"{compatibility.to_version} ({compatibility.compatibility_level})"
        )
    
    def extract_version_from_path(self, path: str) -> Tuple[Optional[str], str]:
        """Extract API version from request path.
        
        Args:
            path: Request path (e.g., '/api/v1/content/generate')
            
        Returns:
            Tuple of (version, path_without_version)
        """
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) < 2 or path_parts[0] != 'api':
            return None, path
        
        potential_version = path_parts[1]
        
        # Check if it's a valid version
        if potential_version in self.supported_versions:
            remaining_path = '/' + '/'.join(path_parts[2:]) if len(path_parts) > 2 else '/'
            return potential_version, remaining_path
        
        # Check for beta or other prefixes
        if potential_version == 'beta':
            # Handle /api/beta/ as latest beta version
            latest_beta = self.get_latest_beta_version()
            if latest_beta:
                remaining_path = '/' + '/'.join(path_parts[2:]) if len(path_parts) > 2 else '/'
                return latest_beta, remaining_path
        
        return None, path
    
    def extract_version_from_header(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract API version from request headers.
        
        Args:
            headers: Request headers
            
        Returns:
            API version if found in headers
        """
        # Check Accept header for version
        accept = headers.get('accept', '')
        if 'application/vnd.techleadautopilot.v' in accept:
            try:
                # Extract version from Accept: application/vnd.techleadautopilot.v1+json
                version_part = accept.split('application/vnd.techleadautopilot.v')[1]
                version_str = version_part.split('+')[0].split(';')[0]
                return f"v{version_str}" if version_str.isdigit() else version_str
            except (IndexError, ValueError):
                pass
        
        # Check custom version header
        api_version = headers.get('api-version') or headers.get('x-api-version')
        if api_version and api_version in self.supported_versions:
            return api_version
        
        return None
    
    def determine_version(self, path: str, headers: Dict[str, str]) -> str:
        """Determine API version from request path and headers.
        
        Args:
            path: Request path
            headers: Request headers
            
        Returns:
            API version to use
        """
        # Priority 1: Path-based version
        path_version, _ = self.extract_version_from_path(path)
        if path_version:
            return path_version
        
        # Priority 2: Header-based version
        header_version = self.extract_version_from_header(headers)
        if header_version:
            return header_version
        
        # Priority 3: Default version
        return self.default_version
    
    def is_version_supported(self, version: str) -> bool:
        """Check if version is supported.
        
        Args:
            version: API version to check
            
        Returns:
            Whether version is supported
        """
        return version in self.supported_versions
    
    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """Get information about specific version.
        
        Args:
            version: API version
            
        Returns:
            Version information if exists
        """
        return self.versions.get(version)
    
    def get_compatibility(self, from_version: str, to_version: str) -> Optional[VersionCompatibility]:
        """Get compatibility information between versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            Compatibility information if available
        """
        return self.compatibility_matrix.get((from_version, to_version))
    
    def get_supported_versions(self) -> List[str]:
        """Get list of all supported versions.
        
        Returns:
            List of supported version strings
        """
        return sorted(self.supported_versions, key=lambda v: version.parse(v.lstrip('v')))
    
    def get_latest_stable_version(self) -> Optional[str]:
        """Get latest stable version.
        
        Returns:
            Latest stable version string
        """
        stable_versions = [
            v for v, info in self.versions.items()
            if info.status == VersionStatus.STABLE
        ]
        
        if not stable_versions:
            return None
            
        return max(stable_versions, key=lambda v: version.parse(v.lstrip('v')))
    
    def get_latest_beta_version(self) -> Optional[str]:
        """Get latest beta version.
        
        Returns:
            Latest beta version string
        """
        beta_versions = [
            v for v, info in self.versions.items()
            if info.status == VersionStatus.BETA
        ]
        
        if not beta_versions:
            return None
            
        return max(beta_versions, key=lambda v: version.parse(v.lstrip('v')))
    
    def get_deprecated_versions(self) -> List[VersionInfo]:
        """Get list of deprecated versions.
        
        Returns:
            List of deprecated version info
        """
        return [
            info for info in self.versions.values()
            if info.is_deprecated
        ]
    
    def deprecate_version(
        self, 
        version: str, 
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None
    ) -> bool:
        """Mark version as deprecated.
        
        Args:
            version: Version to deprecate
            deprecation_date: When version was deprecated
            sunset_date: When version will be sunset
            
        Returns:
            Whether deprecation was successful
        """
        if version not in self.versions:
            return False
        
        version_info = self.versions[version]
        version_info.status = VersionStatus.DEPRECATED
        version_info.deprecation_date = deprecation_date or datetime.now(timezone.utc)
        if sunset_date:
            version_info.sunset_date = sunset_date
        
        logger.warning(f"Deprecated API version {version}")
        return True
    
    def sunset_version(self, version: str) -> bool:
        """Mark version as sunset (no longer supported).
        
        Args:
            version: Version to sunset
            
        Returns:
            Whether sunset was successful
        """
        if version not in self.versions:
            return False
        
        version_info = self.versions[version]
        version_info.status = VersionStatus.SUNSET
        self.supported_versions.discard(version)
        
        logger.warning(f"Sunset API version {version}")
        return True
    
    def get_version_stats(self) -> Dict[str, Any]:
        """Get statistics about API versions.
        
        Returns:
            Dictionary with version statistics
        """
        stats = {
            "total_versions": len(self.versions),
            "supported_versions": len(self.supported_versions),
            "stable_versions": len([
                v for v in self.versions.values()
                if v.status == VersionStatus.STABLE
            ]),
            "beta_versions": len([
                v for v in self.versions.values()
                if v.status == VersionStatus.BETA
            ]),
            "deprecated_versions": len([
                v for v in self.versions.values() 
                if v.status == VersionStatus.DEPRECATED
            ]),
            "sunset_versions": len([
                v for v in self.versions.values()
                if v.status == VersionStatus.SUNSET
            ]),
            "default_version": self.default_version,
            "latest_stable": self.get_latest_stable_version(),
            "latest_beta": self.get_latest_beta_version()
        }
        
        return stats