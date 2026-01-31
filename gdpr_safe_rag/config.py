"""Configuration management using pydantic-settings."""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectionLevel(str, Enum):
    """PII detection sensitivity levels."""

    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class RedactionStrategy(str, Enum):
    """Available redaction strategies."""

    TOKEN = "token"  # [EMAIL_1], [UK_PHONE_1]
    HASH = "hash"  # [EMAIL_a3f5b9]
    CATEGORY = "category"  # [EMAIL]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./gdpr_safe_rag.db",
        description="Database connection URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # PII Detection
    pii_detection_level: DetectionLevel = Field(
        default=DetectionLevel.STRICT,
        description="PII detection sensitivity level",
    )
    pii_default_redaction_strategy: RedactionStrategy = Field(
        default=RedactionStrategy.TOKEN,
        description="Default redaction strategy",
    )

    # Audit Settings
    audit_retention_days: int = Field(
        default=2555,
        description="Number of days to retain audit logs (default ~7 years)",
    )

    # Optional encryption
    pii_encryption_key: Optional[str] = Field(
        default=None,
        description="Base64-encoded encryption key for PII mapping storage",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
