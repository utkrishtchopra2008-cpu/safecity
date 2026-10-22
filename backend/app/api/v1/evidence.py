"""Evidence metadata and short-lived private-content access."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as OrmSession

from app.api.v1.auth import AuthContext, require_roles
from app.core.config import AppSettings, get_settings
from app.db.models import Evidence
from app.db.session import get_db
from app.services.audit import record_security_event
from app.storage.supabase import StorageUnavailable, SupabaseStorage

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceResponse(BaseModel):
    id: UUID
    source_id: UUID
    evidence_type: Literal["original_video", "clip", "frame"]
    mime_type: str
    byte_size: int | None
    sha256: str | None
    status: Literal["processing", "available", "unavailable", "failed"]
    created_at: datetime


def _authorized_evidence(database: OrmSession, evidence_id: UUID) -> Evidence:
    evidence = database.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return evidence


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: UUID,
    request: Request,
    context: AuthContext = Depends(require_roles("operator", "supervisor")),  # noqa: B008
    database: OrmSession = Depends(get_db),  # noqa: B008
) -> EvidenceResponse:
    evidence = _authorized_evidence(database, evidence_id)
    record_security_event(
        database,
        request,
        action="evidence.metadata.read",
        result="success",
        actor=context.user,
        object_type="evidence",
        object_id=str(evidence.id),
    )
    database.commit()
    return EvidenceResponse(
        id=evidence.id,
        source_id=evidence.source_id,
        evidence_type=cast(Literal["original_video", "clip", "frame"], evidence.evidence_type),
        mime_type=evidence.mime_type,
        byte_size=evidence.byte_size,
        sha256=evidence.sha256,
        status=cast(Literal["processing", "available", "unavailable", "failed"], evidence.status),
        created_at=evidence.created_at,
    )


@router.get("/{evidence_id}/content", include_in_schema=True)
async def get_evidence_content(
    evidence_id: UUID,
    request: Request,
    context: AuthContext = Depends(require_roles("operator", "supervisor")),  # noqa: B008
    database: OrmSession = Depends(get_db),  # noqa: B008
    settings: AppSettings = Depends(get_settings),  # noqa: B008
) -> RedirectResponse:
    evidence = _authorized_evidence(database, evidence_id)
    if evidence.status != "available" or evidence.storage_backend != "object":
        raise HTTPException(status_code=503, detail="DEPENDENCY_UNAVAILABLE")
    if settings.storage_backend != "supabase" or not settings.supabase_configured:
        raise HTTPException(status_code=503, detail="DEPENDENCY_UNAVAILABLE")
    database.commit()
    storage = SupabaseStorage(settings)
    try:
        signed_url = await storage.signed_url(evidence.storage_key, expires_in_seconds=120)
    except StorageUnavailable as exc:
        raise HTTPException(status_code=503, detail="DEPENDENCY_UNAVAILABLE") from exc
    finally:
        await storage.close()
    record_security_event(
        database,
        request,
        action="evidence.content.access",
        result="success",
        actor=context.user,
        object_type="evidence",
        object_id=str(evidence.id),
    )
    database.commit()
    return RedirectResponse(
        signed_url,
        status_code=307,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
