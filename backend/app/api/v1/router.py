"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.public_context import router as public_context_router
from app.api.v1.reliability import router as reliability_router
from app.api.v1.sources import router as sources_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(evidence_router)
api_router.include_router(evaluations_router)
api_router.include_router(incidents_router)
api_router.include_router(sources_router)
api_router.include_router(jobs_router)
api_router.include_router(reliability_router)
api_router.include_router(public_context_router)
