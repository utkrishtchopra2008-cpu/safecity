import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import AppSettings
from app.services import tinyfish
from app.services.tinyfish import TinyFishUnavailable


def settings(**overrides: object) -> AppSettings:
    return AppSettings(
        tinyfish_context_enabled=True,
        tinyfish_api_key="server-only-test-secret",
        tinyfish_allowed_domains=["weather.gov.in", "example.gov"],
        **overrides,
    )


def patch_provider(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> list[httpx.Request]:
    requests: list[httpx.Request] = []
    transport = httpx.MockTransport(lambda request: (requests.append(request), response)[1])
    client_class = httpx.AsyncClient

    def factory(**kwargs: object) -> httpx.AsyncClient:
        return client_class(transport=transport, **kwargs)

    monkeypatch.setattr(tinyfish.httpx, "AsyncClient", factory)
    return requests


def test_search_normalizes_bounded_attributed_results_and_secret_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = patch_provider(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "query": "weather advisory monsoon",
                "total_results": 1,
                "page": 0,
                "results": [
                    {
                        "title": "Rain warning",
                        "snippet": "Heavy rain expected.",
                        "site_name": "Weather Service",
                        "url": "https://weather.gov.in/notice/1",
                        "date": datetime.now(UTC).isoformat(),
                    }
                ],
            },
        ),
    )
    results = asyncio.run(
        tinyfish.search_public_context(settings(), "monsoon update", topic="weather_advisory")
    )
    assert len(results) == 1
    assert results[0].title == "Rain warning"
    assert results[0].source_domain == "weather.gov.in"
    assert results[0].freshness == "current"
    assert requests[0].url.host == "api.search.tinyfish.ai"
    assert requests[0].headers["X-API-Key"] == "server-only-test-secret"
    assert requests[0].url.params["include_domains"] == "weather.gov.in,example.gov"


def test_search_rejects_private_data_queries_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tinyfish.httpx,
        "AsyncClient",
        lambda **_: pytest.fail("request must not reach TinyFish"),
    )
    with pytest.raises(ValueError, match="PUBLIC_QUERY_INVALID"):
        asyncio.run(
            tinyfish.search_public_context(
                settings(), "Report to alice@example.com immediately", topic="public_notice"
            )
        )


def test_search_requires_backend_secret_and_feature_flag() -> None:
    with pytest.raises(TinyFishUnavailable):
        asyncio.run(
            tinyfish.search_public_context(
                AppSettings(), "public weather update", topic="weather_advisory"
            )
        )


@pytest.mark.parametrize(
    "raw_url",
    [
        "http://weather.gov.in/private",
        "https://localhost/private",
        "https://127.0.0.1/private",
        "https://weather.gov.in.evil.test/path",
        "https://user:pass@weather.gov.in/private",
        "https://example.com/private",
    ],
)
def test_search_result_url_is_revalidated(raw_url: str) -> None:
    assert tinyfish.validate_public_url(raw_url, ["weather.gov.in"]) is None


def test_search_drops_invalid_urls_and_keeps_unknown_publication_freshness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_provider(
        monkeypatch,
        httpx.Response(
            200,
            content=json.dumps(
                {
                    "results": [
                        {"url": "https://private.example.test/"},
                        {"url": "https://example.gov/item", "title": "Notice"},
                    ]
                }
            ),
        ),
    )
    results = asyncio.run(
        tinyfish.search_public_context(settings(), "public notice update", topic="public_notice")
    )
    assert len(results) == 1
    assert results[0].freshness == "unknown"
    assert results[0].published_at is None


def test_search_rejects_oversized_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = patch_provider(
        monkeypatch,
        httpx.Response(200, content=b"{" + (b" " * tinyfish.MAX_RESPONSE_BYTES) + b"}"),
    )
    with pytest.raises(TinyFishUnavailable):
        asyncio.run(
            tinyfish.search_public_context(settings(), "public notice", topic="public_notice")
        )
    assert requests


def test_search_provider_failure_degrades_without_raw_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_provider(monkeypatch, httpx.Response(429, text="key=do-not-return"))
    with pytest.raises(TinyFishUnavailable, match="PUBLIC_CONTEXT_UNAVAILABLE") as exc:
        asyncio.run(
            tinyfish.search_public_context(settings(), "public notice", topic="public_notice")
        )
    assert "do-not-return" not in str(exc.value)


def test_fetch_normalizes_public_page_and_bounds_text(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = patch_provider(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.gov/notices/1",
                        "final_url": "https://example.gov/notices/1",
                        "title": "Transit update",
                        "description": "A route update.",
                        "published_date": None,
                        "text": "Public page text.",
                    }
                ],
                "errors": [],
            },
        ),
    )
    result = asyncio.run(tinyfish.fetch_public_context(settings(), "https://example.gov/notices/1"))
    assert result.title == "Transit update"
    assert result.text == "Public page text."
    assert result.freshness == "unknown"
    assert requests[0].method == "POST"
    assert requests[0].url.host == "api.fetch.tinyfish.ai"
    assert requests[0].headers["X-API-Key"] == "server-only-test-secret"
    assert requests[0].read() == (
        b'{"urls":["https://example.gov/notices/1"],"format":"markdown",'
        b'"links":false,"image_links":false,"per_url_timeout_ms":15000}'
    )


def test_fetch_rejects_query_parameters_and_untrusted_final_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_class = httpx.AsyncClient
    monkeypatch.setattr(
        tinyfish.httpx,
        "AsyncClient",
        lambda **_: pytest.fail("unsafe URL must not reach TinyFish"),
    )
    with pytest.raises(ValueError, match="PUBLIC_URL_INVALID"):
        asyncio.run(tinyfish.fetch_public_context(settings(), "https://example.gov/a?token=secret"))

    monkeypatch.setattr(tinyfish.httpx, "AsyncClient", client_class)
    patch_provider(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.gov/notices/1",
                        "final_url": "https://169.254.169.254/latest/meta-data",
                        "text": "untrusted page",
                    }
                ]
            },
        ),
    )
    with pytest.raises(TinyFishUnavailable):
        asyncio.run(tinyfish.fetch_public_context(settings(), "https://example.gov/notices/1"))
