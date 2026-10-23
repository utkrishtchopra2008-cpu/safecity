import asyncio

import httpx
import pytest

from app.core.config import AppSettings
from app.storage.supabase import StorageUnavailable, SupabaseStorage


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


def test_signed_url_rejects_traversal_keys_before_network_call() -> None:
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
            await storage.signed_url("evidence/../private.mp4")

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


def test_storage_listing_uses_bounded_private_api_and_normalizes_objects() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=[
                {
                    "name": "source-id/evidence-id/original.mp4",
                    "id": "object-id",
                    "created_at": "2026-10-20T12:00:00Z",
                },
                {"name": "folder", "id": None, "created_at": None},
            ],
        )

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        storage = SupabaseStorage(
            AppSettings(
                supabase_url="https://storage.example.test",
                supabase_service_role_key="test-secret",
            ),
            client,
        )
        return await storage.list_folder("sources/", offset=0, limit=50)

    objects = asyncio.run(run())

    assert requests[0].url.path.endswith("/object/list/safecity-evidence")
    assert requests[0].headers["Authorization"] == "Bearer test-secret"
    assert requests[0].read() == (
        b'{"prefix":"sources/","limit":50,"offset":0,"sortBy":{"column":"name","order":"asc"}}'
    )
    assert objects[0].key == "sources/source-id/evidence-id/original.mp4"
    assert objects[0].is_file is True
    assert objects[0].created_at is not None
    assert objects[1].key == "sources/folder/"
    assert objects[1].is_file is False


def test_storage_listing_rejects_unbounded_response() -> None:
    async def run() -> None:
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=b"[" + (b" " * 1_000_000) + b"]")
            )
        )
        storage = SupabaseStorage(
            AppSettings(
                supabase_url="https://storage.example.test",
                supabase_service_role_key="test-secret",
            ),
            client,
        )
        with pytest.raises(StorageUnavailable):
            await storage.list_folder("sources/", offset=0, limit=50)

    asyncio.run(run())
