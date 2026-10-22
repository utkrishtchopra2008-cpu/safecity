"""FastAPI application entry point for the initial project foundation."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.session import get_engine

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level), format="%(levelname)s %(name)s %(message)s"
)

is_production = settings.app_env == "production"
app = FastAPI(
    title="SafeCity AI API",
    description="Privacy-preserving incident review API with server-managed sessions.",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def add_request_context(request: Request, call_next: Any) -> Any:
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith(f"{settings.api_prefix}/auth/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def problem_response(
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: str,
    *,
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    body: dict[str, Any] = {
        "type": f"https://example.invalid/problems/{code.lower()}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(
        body,
        status_code=status,
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    known = {
        401: ("AUTHENTICATION_REQUIRED", "Authentication required", "Sign in to continue."),
        403: (
            "PERMISSION_DENIED",
            "Permission denied",
            "You are not permitted to perform this action.",
        ),
        404: ("RESOURCE_NOT_FOUND", "Resource not found", "The requested resource is unavailable."),
        409: (
            "RESOURCE_CONFLICT",
            "Resource conflict",
            "The request conflicts with the current resource state.",
        ),
        413: ("FILE_TOO_LARGE", "File too large", "The upload exceeds the configured limit."),
        415: (
            "UNSUPPORTED_MEDIA_TYPE",
            "Unsupported media type",
            "The media format is not supported.",
        ),
        422: ("VALIDATION_ERROR", "Request validation failed", "One or more fields are invalid."),
        429: ("RATE_LIMIT_EXCEEDED", "Too many requests", "Wait before trying again."),
        503: (
            "DEPENDENCY_UNAVAILABLE",
            "Service unavailable",
            "A required service is unavailable.",
        ),
    }
    code, title, detail = known.get(
        exc.status_code,
        ("INTERNAL_ERROR", "Request failed", "The request could not be completed."),
    )
    if isinstance(exc.detail, str) and exc.detail in {item[0] for item in known.values()}:
        code = exc.detail
    return problem_response(request, exc.status_code, code, title, detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(part) for part in error.get("loc", ())), "message": "Invalid value."}
        for error in exc.errors()
    ]
    return problem_response(
        request,
        422,
        "VALIDATION_ERROR",
        "Request validation failed",
        "One or more fields are invalid.",
        errors=errors,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    if isinstance(exc, IntegrityError):
        return problem_response(
            request,
            409,
            "RESOURCE_CONFLICT",
            "Resource conflict",
            "The request conflicts with the current resource state.",
        )
    if isinstance(exc, OperationalError):
        return problem_response(
            request,
            503,
            "DEPENDENCY_UNAVAILABLE",
            "Service unavailable",
            "The database is temporarily unavailable.",
        )
    return problem_response(
        request, 500, "INTERNAL_ERROR", "Request failed", "The request could not be completed."
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("safecity.api").error(
        "request_failed request_id=%s category=internal_error",
        getattr(request.state, "request_id", "unavailable"),
    )
    return problem_response(
        request, 500, "INTERNAL_ERROR", "Request failed", "The request could not be completed."
    )


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
def readiness() -> JSONResponse:
    """Probe required local dependencies without exposing connection details."""
    database_state = "not_configured"
    if settings.database_url is not None:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            database_state = "available"
        except Exception:
            database_state = "unavailable"
    storage_state = (
        "configured"
        if settings.storage_backend == "local" or settings.supabase_configured
        else "not_configured"
    )
    healthy = database_state == "available"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ready" if healthy else "not_ready",
            "checks": {
                "configuration": "valid",
                "database": database_state,
                "storage": storage_state,
                "worker": "not_reported",
                "tinyfish": "configured" if settings.tinyfish_configured else "disabled",
            },
        },
    )
