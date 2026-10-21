"""Versioned API namespace. Feature routers are added in later implementation phases."""

from app.api.v1.router import api_router

__all__ = ["api_router"]
