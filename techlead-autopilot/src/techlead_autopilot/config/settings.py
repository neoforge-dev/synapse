"""Application settings and configuration management."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTOPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = Field(default="TechLead AutoPilot", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key for JWT tokens")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # Database
    database_url: str = Field(default="postgresql://user:password@localhost:5432/techlead_autopilot", description="Database connection URL")
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Redis (Caching & Sessions)
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_key_prefix: str = Field(default="autopilot:", description="Redis key prefix")
    
    # LinkedIn API
    linkedin_client_id: str = Field(default="", description="LinkedIn OAuth client ID")
    linkedin_client_secret: str = Field(default="", description="LinkedIn OAuth client secret")
    linkedin_redirect_uri: str = Field(default="http://localhost:8000/auth/linkedin/callback", description="LinkedIn OAuth redirect URI")
    
    # OpenAI API
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")
    
    # Anthropic API
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model to use")
    
    # Stripe (Billing)
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key")
    stripe_secret_key: str = Field(default="", description="Stripe secret key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook secret")
    
    # Content Generation
    content_generation_provider: str = Field(default="openai", description="Content generation provider (openai, anthropic)")
    max_content_length: int = Field(default=3000, description="Maximum content length in characters")
    content_templates_path: str = Field(default="templates/", description="Path to content templates")
    
    # Lead Detection
    lead_detection_enabled: bool = Field(default=True, description="Enable lead detection")
    lead_score_threshold: float = Field(default=0.7, description="Lead score threshold for notifications")
    
    # Analytics
    analytics_enabled: bool = Field(default=True, description="Enable analytics tracking")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    
    # Celery (Background Tasks)
    celery_broker_url: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", description="Celery result backend")
    
    # AWS (File Storage)
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_s3_bucket: Optional[str] = Field(default=None, description="AWS S3 bucket name")
    
    # Monitoring & Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json, console)")
    log_max_bytes: int = Field(default=52428800, description="Maximum log file size in bytes (50MB)")
    log_backup_count: int = Field(default=10, description="Number of backup log files to keep")
    log_audit_backup_count: int = Field(default=20, description="Number of backup audit log files to keep")
    structured_logging: bool = Field(default=True, description="Enable structured logging")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    sentry_traces_sample_rate: float = Field(default=0.1, description="Sentry traces sample rate")
    
    # Health Checks
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @field_validator("content_generation_provider")
    @classmethod
    def validate_content_provider(cls, v: str) -> str:
        """Validate content generation provider."""
        allowed = ["openai", "anthropic"]
        if v not in allowed:
            raise ValueError(f"Content provider must be one of: {allowed}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        allowed = ["json", "console"]
        if v.lower() not in allowed:
            raise ValueError(f"Log format must be one of: {allowed}")
        return v.lower()
    
    @field_validator("sentry_traces_sample_rate")
    @classmethod
    def validate_sentry_sample_rate(cls, v: float) -> float:
        """Validate Sentry traces sample rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Sentry traces sample rate must be between 0.0 and 1.0")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()