"""Validated application configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class AppSettings(BaseModel):
    """Configuration foundation. Database and feature wiring are added in later phases."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_prefix: str = "/api/v1"
    public_app_origin: str = "http://localhost:5173"
    database_url: SecretStr | None = None
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    csrf_allowed_origins: list[str] = Field(default_factory=list)
    cors_origins: list[str] = Field(default_factory=list)
    local_media_root: Path = Path(".data/media")
    storage_backend: Literal["local", "object_storage"] = "local"
    max_upload_bytes: int = Field(default=104_857_600, ge=1, le=2_147_483_648)
    detector_backend: Literal["simulated", "local"] = "simulated"
    detector_version: str = "simulated-v1"
    worker_poll_interval_seconds: float = Field(default=2.0, gt=0, le=300)
    worker_max_attempts: int = Field(default=3, ge=1, le=20)
    tinyfish_context_enabled: bool = False
    tinyfish_api_key: SecretStr | None = None
    tinyfish_request_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    tinyfish_max_results_per_refresh: int = Field(default=5, ge=1, le=10)
    tinyfish_context_ttl_seconds: int = Field(default=1800, ge=60, le=604_800)
    tinyfish_allowed_domains: list[str] = Field(default_factory=list)

    @field_validator("database_url", "tinyfish_api_key", mode="before")
    @classmethod
    def blank_secret_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("csrf_allowed_origins", "cors_origins", "tinyfish_allowed_domains", mode="before")
    @classmethod
    def parse_comma_separated_values(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        normalized = "/" + value.strip("/")
        if normalized == "/":
            raise ValueError("API_PREFIX must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_production_requirements(self) -> AppSettings:
        if self.app_env == "production":
            if self.database_url is None:
                raise ValueError("DATABASE_URL is required in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if not self.public_app_origin.startswith("https://"):
                raise ValueError("PUBLIC_APP_ORIGIN must use HTTPS in production")
        return self

    @property
    def tinyfish_configured(self) -> bool:
        """Return whether both the context feature and its server-side API key are present."""
        return self.tinyfish_context_enabled and self.tinyfish_api_key is not None

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> AppSettings:
        """Create validated settings without requiring a settings-specific dependency."""
        source = os.environ if environ is None else environ
        environment_map = {
            "APP_ENV": "app_env",
            "LOG_LEVEL": "log_level",
            "API_PREFIX": "api_prefix",
            "PUBLIC_APP_ORIGIN": "public_app_origin",
            "DATABASE_URL": "database_url",
            "COOKIE_SECURE": "cookie_secure",
            "COOKIE_SAMESITE": "cookie_samesite",
            "CSRF_ALLOWED_ORIGINS": "csrf_allowed_origins",
            "CORS_ORIGINS": "cors_origins",
            "LOCAL_MEDIA_ROOT": "local_media_root",
            "STORAGE_BACKEND": "storage_backend",
            "MAX_UPLOAD_BYTES": "max_upload_bytes",
            "DETECTOR_BACKEND": "detector_backend",
            "DETECTOR_VERSION": "detector_version",
            "WORKER_POLL_INTERVAL_SECONDS": "worker_poll_interval_seconds",
            "WORKER_MAX_ATTEMPTS": "worker_max_attempts",
            "TINYFISH_CONTEXT_ENABLED": "tinyfish_context_enabled",
            "TINYFISH_API_KEY": "tinyfish_api_key",
            "TINYFISH_REQUEST_TIMEOUT_SECONDS": "tinyfish_request_timeout_seconds",
            "TINYFISH_MAX_RESULTS_PER_REFRESH": "tinyfish_max_results_per_refresh",
            "TINYFISH_CONTEXT_TTL_SECONDS": "tinyfish_context_ttl_seconds",
            "TINYFISH_ALLOWED_DOMAINS": "tinyfish_allowed_domains",
        }
        values = {
            field_name: source[environment_name]
            for environment_name, field_name in environment_map.items()
            if environment_name in source
        }
        return cls.model_validate(values)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached settings object for this process."""
    return AppSettings.from_environment()
