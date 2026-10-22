"""Private Supabase Storage adapter. Authorization belongs to the calling service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import AppSettings


class StorageUnavailable(RuntimeError):
    """Raised when the configured private storage service cannot complete an operation."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class SupabaseStorage:
    def __init__(self, settings: AppSettings, client: httpx.AsyncClient | None = None) -> None:
        if not settings.supabase_configured or settings.supabase_url is None:
            raise ValueError("Supabase Storage configuration is incomplete")
        self._base_url = settings.supabase_url.rstrip("/") + "/storage/v1"
        self._bucket = settings.supabase_storage_bucket
        assert settings.supabase_service_role_key is not None
        self._headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key.get_secret_value()}",
            "apikey": settings.supabase_service_role_key.get_secret_value(),
        }
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _object_url(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/") or "\\" in key:
            raise ValueError("Storage key must be a server-generated relative object key")
        return f"{self._base_url}/object/{quote(self._bucket, safe='')}/{quote(key, safe='/')}"

    async def upload(
        self,
        key: str,
        chunks: AsyncIterator[bytes],
        *,
        content_type: str,
        content_length: int,
    ) -> None:
        """Upload a prevalidated bounded stream without assembling it in memory."""
        try:
            response = await self._client.post(
                self._object_url(key),
                content=chunks,
                headers={
                    **self._headers,
                    "Content-Type": content_type,
                    "Content-Length": str(content_length),
                    "x-upsert": "false",
                    "Cache-Control": "max-age=0",
                },
            )
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise StorageUnavailable("Private evidence upload failed") from exc

    async def exists(self, key: str) -> bool:
        try:
            response = await self._client.head(self._object_url(key), headers=self._headers)
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            raise StorageUnavailable("Private evidence availability could not be checked") from exc

    async def download_to_path(self, key: str, path: Path, *, maximum_bytes: int) -> int:
        """Stream a private object to a temporary file with a strict byte ceiling."""
        byte_count = 0
        try:
            async with self._client.stream(
                "GET", self._object_url(key), headers=self._headers
            ) as response:
                response.raise_for_status()
                declared_length = response.headers.get("content-length")
                if declared_length is not None and int(declared_length) > maximum_bytes:
                    raise StorageUnavailable(
                        "Stored media exceeds the configured byte limit", retryable=False
                    )
                with path.open("xb") as destination:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        byte_count += len(chunk)
                        if byte_count > maximum_bytes:
                            raise StorageUnavailable(
                                "Stored media exceeds the configured byte limit", retryable=False
                            )
                        destination.write(chunk)
            return byte_count
        except (httpx.HTTPError, OSError, ValueError, StorageUnavailable) as exc:
            path.unlink(missing_ok=True)
            if isinstance(exc, StorageUnavailable):
                raise
            retryable = (
                exc.response.status_code in {408, 425, 429} or exc.response.status_code >= 500
                if isinstance(exc, httpx.HTTPStatusError)
                else isinstance(exc, httpx.HTTPError)
            )
            raise StorageUnavailable(
                "Private evidence download failed", retryable=retryable
            ) from exc

    async def signed_url(self, key: str, *, expires_in_seconds: int = 120) -> str:
        """Create a short-lived signed URL after the caller has authorized the evidence."""
        if not 1 <= expires_in_seconds <= 300:
            raise ValueError("Signed URL lifetime must be between 1 and 300 seconds")
        try:
            response = await self._client.post(
                f"{self._base_url}/object/sign/{quote(self._bucket, safe='')}/{quote(key, safe='/')}",
                headers={
                    **self._headers,
                    "Content-Type": "application/json",
                    "Cache-Control": "no-store",
                },
                json={"expiresIn": expires_in_seconds},
            )
            response.raise_for_status()
            signed_path = response.json().get("signedURL")
            if not isinstance(signed_path, str) or not signed_path.startswith("/"):
                raise StorageUnavailable("Storage returned an invalid signed URL")
            return self._base_url + signed_path
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            if isinstance(exc, StorageUnavailable):
                raise
            raise StorageUnavailable("Private evidence URL could not be created") from exc

    async def delete(self, key: str) -> None:
        """Delete only when called by an explicit authorized cleanup workflow."""
        try:
            response = await self._client.delete(self._object_url(key), headers=self._headers)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            raise StorageUnavailable("Private evidence cleanup failed") from exc
