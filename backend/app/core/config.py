"""Validated application configuration loaded from environment variables."""

from __future__ import annotations

import ipaddress
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
    session_ttl_seconds: int = Field(default=28_800, ge=300, le=604_800)
    session_idle_ttl_seconds: int = Field(default=1_800, ge=60, le=86_400)
    session_csrf_secret: SecretStr | None = None
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    csrf_allowed_origins: list[str] = Field(default_factory=list)
    cors_origins: list[str] = Field(default_factory=list)
    local_media_root: Path = Path(".data/media")
    storage_backend: Literal["local", "supabase"] = "local"
    max_upload_bytes: int = Field(default=104_857_600, ge=1, le=2_147_483_648)
    max_upload_duration_seconds: int = Field(default=900, ge=1, le=86_400)
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "safecity-evidence"
    detector_backend: Literal["simulated", "opencv_zoo"] = "simulated"
    detector_version: str = "simulated-v1"
    detector_model_dir: Path = Path("../.data/models")
    worker_poll_interval_seconds: float = Field(default=2.0, gt=0, le=300)
    worker_max_attempts: int = Field(default=3, ge=1, le=20)
    tinyfish_context_enabled: bool = False
    tinyfish_api_key: SecretStr | None = None
    tinyfish_request_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    tinyfish_max_results_per_refresh: int = Field(default=5, ge=1, le=10)
    tinyfish_context_ttl_seconds: int = Field(default=1800, ge=60, le=604_800)
    tinyfish_allowed_domains: list[str] = Field(default_factory=list)

    @field_validator(
        "database_url",
        "tinyfish_api_key",
        "supabase_service_role_key",
        "session_csrf_secret",
        mode="before",
    )
    @classmethod
    def blank_secret_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "csrf_allowed_origins", "cors_origins", "tinyfish_allowed_domains", mode="before"
    )
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

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("SUPABASE_URL must use HTTPS")
        return value.rstrip("/") if value is not None else None

    @field_validator("supabase_storage_bucket")
    @classmethod
    def validate_storage_bucket(cls, value: str) -> str:
        if not value or "/" in value or value in {".", ".."}:
            raise ValueError("SUPABASE_STORAGE_BUCKET must be one bucket name")
        return value

    @field_validator("tinyfish_allowed_domains")
    @classmethod
    def validate_tinyfish_domains(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            domain = value.strip().lower().rstrip(".")
            if not domain or "://" in domain or "/" in domain or "@" in domain:
                raise ValueError("TINYFISH_ALLOWED_DOMAINS must contain hostnames only")
            try:
                address = ipaddress.ip_address(domain)
            except ValueError:
                address = None
            if address is not None:
                if not address.is_global:
                    raise ValueError("TINYFISH_ALLOWED_DOMAINS must be public hosts")
            else:
                labels = domain.split(".")
                if (
                    len(labels) < 2
                    or any(not label or len(label) > 63 for label in labels)
                    or any(not label[0].isalnum() or not label[-1].isalnum() for label in labels)
                    or any(
                        not all(char.isalnum() or char == "-" for char in label) for label in labels
                    )
                    or labels[-1] in {"localhost", "local", "internal", "test", "invalid"}
                ):
                    raise ValueError("TINYFISH_ALLOWED_DOMAINS must contain public hostnames")
            normalized.append(domain)
        return list(dict.fromkeys(normalized))

    @field_validator("session_csrf_secret")
    @classmethod
    def validate_csrf_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("SESSION_CSRF_SECRET must contain at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_production_requirements(self) -> AppSettings:
        if self.session_idle_ttl_seconds > self.session_ttl_seconds:
            raise ValueError("SESSION_IDLE_TTL_SECONDS must not exceed SESSION_TTL_SECONDS")
        if self.app_env == "production":
            if self.database_url is None:
                raise ValueError("DATABASE_URL is required in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.session_csrf_secret is None:
                raise ValueError("SESSION_CSRF_SECRET is required in production")
            if not self.public_app_origin.startswith("https://"):
                raise ValueError("PUBLIC_APP_ORIGIN must use HTTPS in production")
            if self.storage_backend != "supabase":
                raise ValueError("STORAGE_BACKEND must be supabase in production")
            if not self.supabase_configured:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase storage"
                )
        return self

    @property
    def tinyfish_configured(self) -> bool:
        """Return whether both the context feature and its server-side API key are present."""
        return self.tinyfish_context_enabled and self.tinyfish_api_key is not None

    @property
    def supabase_configured(self) -> bool:
        """Return whether the private Supabase Storage adapter has server credentials."""
        return self.supabase_url is not None and self.supabase_service_role_key is not None

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
            "SESSION_TTL_SECONDS": "session_ttl_seconds",
            "SESSION_IDLE_TTL_SECONDS": "session_idle_ttl_seconds",
            "SESSION_CSRF_SECRET": "session_csrf_secret",
            "COOKIE_SECURE": "cookie_secure",
            "COOKIE_SAMESITE": "cookie_samesite",
            "CSRF_ALLOWED_ORIGINS": "csrf_allowed_origins",
            "CORS_ORIGINS": "cors_origins",
            "LOCAL_MEDIA_ROOT": "local_media_root",
            "STORAGE_BACKEND": "storage_backend",
            "MAX_UPLOAD_BYTES": "max_upload_bytes",
            "MAX_UPLOAD_DURATION_SECONDS": "max_upload_duration_seconds",
            "SUPABASE_URL": "supabase_url",
            "SUPABASE_SERVICE_ROLE_KEY": "supabase_service_role_key",
            "SUPABASE_STORAGE_BUCKET": "supabase_storage_bucket",
            "DETECTOR_BACKEND": "detector_backend",
            "DETECTOR_VERSION": "detector_version",
            "DETECTOR_MODEL_DIR": "detector_model_dir",
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
