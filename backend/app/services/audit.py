"""Append-only security audit writes; sensitive request data is never recorded."""

from __future__ import annotations

from typing import Literal

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, User


def record_security_event(
    database: Session,
    request: Request,
    *,
    action: str,
    result: Literal["success", "denied", "failure"],
    actor: User | None = None,
    object_type: str = "authentication",
    object_id: str | None = None,
) -> None:
    """Add a minimal audit record to the caller's current transaction."""
    database.add(
        AuditEvent(
            actor_user_id=actor.id if actor is not None else None,
            actor_role=actor.role if actor is not None else "anonymous",
            action=action,
            object_type=object_type,
            object_id=object_id or (str(actor.id) if actor is not None else None),
            result=result,
            correlation_id=getattr(request.state, "request_id", None),
        )
    )
