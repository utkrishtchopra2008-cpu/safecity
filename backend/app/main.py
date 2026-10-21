"""FastAPI application entry point for the initial project foundation."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level), format="%(levelname)s %(name)s %(message)s")

is_production = settings.app_env == "production"
app = FastAPI(
    title="SafeCity AI API",
    description="Foundation API. Product endpoints are added in subsequent implementation phases.",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

app.include_router(api_router, prefix=settings.api_prefix)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )


@app.get("/", include_in_schema=False)
def service_info() -> dict[str, str]:
    """Return minimal service metadata without implying feature readiness."""
    return {
        "service": "SafeCity AI API",
        "stage": "foundation",
        "liveness": "/health/live",
    }


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    """Return process liveness; this endpoint does not probe external dependencies."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness() -> dict[str, Any]:
    """Report configuration readiness for the scaffold; DB probing is a later phase."""
    database_state = "configured_not_probed" if settings.database_url else "not_configured_yet"
    return {
        "status": "ready",
        "checks": {
            "configuration": "valid",
            "database": database_state,
            "feature_workflows": "not_implemented_in_foundation",
        },
    }
