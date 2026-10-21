import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_context_integration_is_disabled_by_default() -> None:
    settings = AppSettings()

    assert settings.tinyfish_context_enabled is False
    assert settings.tinyfish_configured is False
    assert settings.tinyfish_api_key is None


def test_csv_configuration_values_are_parsed() -> None:
    settings = AppSettings.model_validate(
        {
            "cors_origins": "http://localhost:5173, https://example.test",
            "tinyfish_allowed_domains": "weather.gov.in, example.gov",
        }
    )

    assert settings.cors_origins == ["http://localhost:5173", "https://example.test"]
    assert settings.tinyfish_allowed_domains == ["weather.gov.in", "example.gov"]


def test_production_requires_database_and_secure_cookies() -> None:
    with pytest.raises(ValidationError):
        AppSettings(app_env="production")


def test_production_rejects_insecure_cookie_configuration() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            app_env="production",
            database_url="postgresql+psycopg://safe:placeholder@db.example.test/safecity",
            cookie_secure=False,
            public_app_origin="https://safecity.example.test",
        )


def test_production_requires_https_origin_even_for_non_local_hosts() -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            app_env="production",
            database_url="postgresql+psycopg://safe:placeholder@db.example.test/safecity",
            cookie_secure=True,
            public_app_origin="http://safecity.example.test",
        )
