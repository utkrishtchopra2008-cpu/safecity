"""Bounded, server-only TinyFish Search client with normalized public results."""

from __future__ import annotations

import ipaddress
import json
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import AppSettings

SEARCH_URL = "https://api.search.tinyfish.ai"
MAX_RESPONSE_BYTES = 512_000
MAX_SNIPPET_CHARS = 1_200
MAX_TITLE_CHARS = 400
PERSONAL_DATA_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\w)\+?\d[\d ().-]{7,}\d(?!\w)"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b"),
)


class TinyFishUnavailable(RuntimeError):
    """Safe provider failure; the secret and provider body are never surfaced."""


class SearchResult(BaseModel):
    title: str
    snippet: str
    publisher: str | None
    source_domain: str
    source_url: str
    published_at: datetime | None
    retrieved_at: datetime
    freshness: str


class _RawResult(BaseModel):
    title: str | None = None
    snippet: str | None = None
    site_name: str | None = None
    publisher: str | None = None
    url: str
    date: str | None = None


class FetchResult(BaseModel):
    title: str
    description: str | None
    text: str
    publisher: str
    source_domain: str
    source_url: str
    published_at: datetime | None
    retrieved_at: datetime
    freshness: str


class _RawFetchResult(BaseModel):
    url: str
    final_url: str
    title: str | None = None
    description: str | None = None
    published_date: str | None = None
    text: str | None = None


def validate_public_url(
    raw_url: str, allowed_domains: list[str], *, allow_query: bool = True
) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(raw_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        if len(raw_url) > 2_000:
            return None
        if not allow_query and (parsed.query or parsed.fragment):
            return None
        if not allow_query and any(pattern.search(raw_url) for pattern in PERSONAL_DATA_PATTERNS):
            return None
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test")):
            return None
        if host.endswith(".") or not any(
            host == domain.lower().strip(".") or host.endswith("." + domain.lower().strip("."))
            for domain in allowed_domains
        ):
            return None
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return None
        except ValueError:
            pass
        return host, raw_url
    except ValueError:
        return None


def validate_search_query(query: str) -> str:
    value = " ".join(query.split())
    if not 3 <= len(value) <= 240 or any(
        pattern.search(value) for pattern in PERSONAL_DATA_PATTERNS
    ):
        raise ValueError("PUBLIC_QUERY_INVALID")
    if "://" in value or "\\" in value:
        raise ValueError("PUBLIC_QUERY_INVALID")
    return value


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC)
    except ValueError:
        return None


async def search_public_context(
    settings: AppSettings, query: str, *, topic: str, recency_minutes: int | None = None
) -> list[SearchResult]:
    safe_query = validate_search_query(query)
    if not settings.tinyfish_context_enabled or not settings.tinyfish_configured:
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
    domains = [domain.strip().lower().strip(".") for domain in settings.tinyfish_allowed_domains]
    if not domains:
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
    freshness_minutes = (
        min(settings.tinyfish_context_ttl_seconds // 60, 5256000)
        if recency_minutes is None
        else recency_minutes
    )
    if not 1 <= freshness_minutes <= 5256000:
        raise ValueError("PUBLIC_CONTEXT_WINDOW_INVALID")
    params = {
        "query": f"{topic.replace('_', ' ')} {safe_query}",
        "domain_type": "news",
        "recency_minutes": str(freshness_minutes),
        "include_domains": ",".join(domains),
    }
    headers = {"X-API-Key": settings.tinyfish_api_key.get_secret_value()}  # type: ignore[union-attr]
    timeout = httpx.Timeout(settings.tinyfish_request_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            async with client.stream("GET", SEARCH_URL, params=params, headers=headers) as response:
                if response.status_code in {401, 403, 429} or response.status_code >= 500:
                    raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
                if response.status_code != 200:
                    raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
                    chunks.append(chunk)
    except TinyFishUnavailable:
        raise
    except (httpx.HTTPError, TimeoutError):
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE") from None

    try:
        payload = json.loads(b"".join(chunks))
        raw_results = payload["results"]
        if not isinstance(raw_results, list):
            raise ValueError
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE") from None

    now = datetime.now(UTC)
    results: list[SearchResult] = []
    for raw in raw_results[: settings.tinyfish_max_results_per_refresh]:
        try:
            result = _RawResult.model_validate(raw)
        except (ValidationError, TypeError):
            continue
        valid_url = validate_public_url(result.url, domains)
        if valid_url is None:
            continue
        host, url = valid_url
        published_at = _parse_date(result.date)
        if published_at is None:
            freshness = "unknown"
        elif published_at < now - timedelta(seconds=settings.tinyfish_context_ttl_seconds):
            freshness = "stale"
        else:
            freshness = "current"
        results.append(
            SearchResult(
                title=(result.title or "Public source")[:MAX_TITLE_CHARS],
                snippet=(result.snippet or "")[:MAX_SNIPPET_CHARS],
                publisher=(result.publisher or result.site_name or host)[:200],
                source_domain=host,
                source_url=url,
                published_at=published_at,
                retrieved_at=now,
                freshness=freshness,
            )
        )
    return results


async def fetch_public_context(settings: AppSettings, public_url: str) -> FetchResult:
    """Fetch one allowlisted public page as bounded Markdown text."""
    if not settings.tinyfish_context_enabled or not settings.tinyfish_configured:
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
    domains = [domain.strip().lower().strip(".") for domain in settings.tinyfish_allowed_domains]
    validated = validate_public_url(public_url, domains, allow_query=False)
    if not domains or validated is None:
        raise ValueError("PUBLIC_URL_INVALID")
    _, normalized_url = validated
    headers = {"X-API-Key": settings.tinyfish_api_key.get_secret_value()}  # type: ignore[union-attr]
    timeout = httpx.Timeout(settings.tinyfish_request_timeout_seconds)
    request_body = {
        "urls": [normalized_url],
        "format": "markdown",
        "links": False,
        "image_links": False,
        "per_url_timeout_ms": min(
            110_000, max(1, int(settings.tinyfish_request_timeout_seconds * 1000))
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            async with client.stream(
                "POST", "https://api.fetch.tinyfish.ai", json=request_body, headers=headers
            ) as response:
                if response.status_code != 200:
                    raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE")
                    chunks.append(chunk)
    except TinyFishUnavailable:
        raise
    except (httpx.HTTPError, TimeoutError):
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE") from None
    try:
        payload = json.loads(b"".join(chunks))
        raw_results = payload["results"]
        if not isinstance(raw_results, list) or not raw_results:
            raise ValueError
        result = _RawFetchResult.model_validate(raw_results[0])
        if result.url != normalized_url:
            raise ValueError
        final = validate_public_url(result.final_url, domains, allow_query=False)
        if final is None or not result.text or not result.text.strip():
            raise ValueError
        final_host, final_url = final
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, ValidationError):
        raise TinyFishUnavailable("PUBLIC_CONTEXT_UNAVAILABLE") from None

    now = datetime.now(UTC)
    published_at = _parse_date(result.published_date)
    if published_at is None:
        freshness = "unknown"
    elif published_at < now - timedelta(seconds=settings.tinyfish_context_ttl_seconds):
        freshness = "stale"
    else:
        freshness = "current"
    return FetchResult(
        title=(result.title or "Public source")[:MAX_TITLE_CHARS],
        description=(result.description or "")[:MAX_SNIPPET_CHARS] or None,
        text=result.text[:MAX_SNIPPET_CHARS],
        publisher=final_host,
        source_domain=final_host,
        source_url=final_url,
        published_at=published_at,
        retrieved_at=now,
        freshness=freshness,
    )
