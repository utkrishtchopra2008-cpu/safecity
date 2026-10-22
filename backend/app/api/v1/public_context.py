"""Authorized, rate-limited public-web search. Provider secrets stay server-side."""

from __future__ import annotations

import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth import AuthContext, require_csrf, require_roles
from app.core.config import AppSettings, get_settings
from app.services.tinyfish import (
    FetchResult,
    SearchResult,
    TinyFishUnavailable,
    fetch_public_context,
    search_public_context,
)

router = APIRouter(prefix="/public-context", tags=["public-context"])
_last_search_by_user: dict[UUID, float] = {}
_last_fetch_by_user: dict[UUID, float] = {}
_search_url_cache: dict[UUID, tuple[float, set[str]]] = {}
USER_SEARCH_COOLDOWN_SECONDS = 10.0
SEARCH_URL_CACHE_SECONDS = 600.0


def _prune_user_state(now: float) -> None:
    for last_by_user in (_last_search_by_user, _last_fetch_by_user):
        for user_id, previous in list(last_by_user.items()):
            if now - previous >= SEARCH_URL_CACHE_SECONDS:
                last_by_user.pop(user_id, None)
    for user_id, (created_at, _) in list(_search_url_cache.items()):
        if now - created_at >= SEARCH_URL_CACHE_SECONDS:
            _search_url_cache.pop(user_id, None)


class PublicSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=240)
    topic: Literal[
        "weather_advisory",
        "transport_disruption",
        "public_notice",
        "public_event",
        "emergency_advisory",
        "other",
    ]


class PublicSearchResponse(BaseModel):
    status: Literal["available", "empty"]
    results: list[SearchResult]
    note: str


class PublicFetchRequest(BaseModel):
    source_url: str = Field(min_length=1, max_length=2_000)


@router.post("/search", response_model=PublicSearchResponse)
async def search_context(
    body: PublicSearchRequest,
    context: AuthContext = Depends(  # noqa: B008
        require_roles("operator", "supervisor", "technical_admin")  # noqa: B008
    ),
    _csrf: AuthContext = Depends(require_csrf),  # noqa: B008
    settings: AppSettings = Depends(get_settings),  # noqa: B008
) -> PublicSearchResponse:
    now = time.monotonic()
    _prune_user_state(now)
    previous = _last_search_by_user.get(context.user.id)
    if previous is not None and now - previous < USER_SEARCH_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Please wait before starting another public context search.",
            headers={"Retry-After": str(int(USER_SEARCH_COOLDOWN_SECONDS - (now - previous)) + 1)},
        )
    _last_search_by_user[context.user.id] = now
    try:
        results = await search_public_context(settings, body.query, topic=body.topic)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="PUBLIC_QUERY_INVALID") from exc
    except TinyFishUnavailable as exc:
        raise HTTPException(status_code=503, detail="PUBLIC_CONTEXT_UNAVAILABLE") from exc
    _search_url_cache[context.user.id] = (now, {item.source_url for item in results})
    return PublicSearchResponse(
        status="available" if results else "empty",
        results=results,
        note=(
            "Public context is external information and does not verify, create, suppress, or reclassify video incidents."
        ),
    )


@router.post("/fetch", response_model=FetchResult)
async def fetch_context(
    body: PublicFetchRequest,
    context: AuthContext = Depends(  # noqa: B008
        require_roles("operator", "supervisor", "technical_admin")  # noqa: B008
    ),
    _csrf: AuthContext = Depends(require_csrf),  # noqa: B008
    settings: AppSettings = Depends(get_settings),  # noqa: B008
) -> FetchResult:
    now = time.monotonic()
    now = time.monotonic()
    _prune_user_state(now)
    previous = _last_fetch_by_user.get(context.user.id)
    if previous is not None and now - previous < USER_SEARCH_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Please wait before starting another public context request.",
            headers={"Retry-After": str(int(USER_SEARCH_COOLDOWN_SECONDS - (now - previous)) + 1)},
        )
    cached = _search_url_cache.get(context.user.id)
    if (
        cached is None
        or now - cached[0] >= SEARCH_URL_CACHE_SECONDS
        or body.source_url not in cached[1]
    ):
        raise HTTPException(status_code=422, detail="PUBLIC_URL_INVALID")
    _last_fetch_by_user[context.user.id] = now
    try:
        return await fetch_public_context(settings, body.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="PUBLIC_URL_INVALID") from exc
    except TinyFishUnavailable as exc:
        raise HTTPException(status_code=503, detail="PUBLIC_CONTEXT_UNAVAILABLE") from exc
