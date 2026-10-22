import asyncio

import httpx
import pytest

from app.core.config import AppSettings
from app.storage.supabase import SupabaseStorage


def test_signed_url_is_requested_from_private_bucket() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"signedURL": "/object/sign/safecity-evidence/a.mp4?token=short"}
        )

    async def run() -> str:
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        storage = SupabaseStorage(
            AppSettings(
                supabase_url="https://storage.example.test",
                supabase_service_role_key="test-secret",
            ),
            client,
        )
        return await storage.signed_url("a.mp4", expires_in_seconds=120)

    result = asyncio.run(run())

    assert (
        result
        == "https://storage.example.test/storage/v1/object/sign/safecity-evidence/a.mp4?token=short"
    )
    assert requests[0].method == "POST"
    assert requests[0].headers["Authorization"] == "Bearer test-secret"
    assert requests[0].read() == b'{"expiresIn":120}'


def test_storage_rejects_traversal_keys_before_network_call() -> None:
    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("network called"))
        )
        storage = SupabaseStorage(
            AppSettings(
                supabase_url="https://storage.example.test",
                supabase_service_role_key="test-secret",
            ),
            client,
        )
        with pytest.raises(ValueError):
            await storage.exists("evidence/../private.mp4")

    asyncio.run(run())


def test_signed_url_lifetime_is_bounded() -> None:
    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("network called"))
        )
        storage = SupabaseStorage(
            AppSettings(
                supabase_url="https://storage.example.test",
                supabase_service_role_key="test-secret",
            ),
            client,
        )
        with pytest.raises(ValueError):
            await storage.signed_url("evidence/a.mp4", expires_in_seconds=3600)

    asyncio.run(run())
