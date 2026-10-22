"""Explicit orphan inventory and cleanup for generated source-upload objects."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.db.models import Evidence
from app.storage.supabase import ListedStorageObject, StorageUnavailable, SupabaseStorage

GENERATED_UPLOAD_KEY = re.compile(
    r"^sources/(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/"
    r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/"
    r"original\.(?:mp4|m4v|mov|avi|mkv)$"
)
LIST_PAGE_SIZE = 100
MAX_SCANNED_OBJECTS = 5_000


async def list_source_objects(storage: SupabaseStorage) -> list[ListedStorageObject]:
    """Walk only the generated `sources/` namespace with bounded paginated calls."""
    folders = ["sources/"]
    files: list[ListedStorageObject] = []
    seen_folders = {"sources/"}
    while folders:
        folder = folders.pop()
        offset = 0
        while True:
            page = await storage.list_folder(folder, offset=offset, limit=LIST_PAGE_SIZE)
            if not page:
                break
            for item in page:
                if item.is_file:
                    files.append(item)
                    if len(files) > MAX_SCANNED_OBJECTS:
                        raise StorageUnavailable(
                            "Orphan scan exceeded its safe object limit", retryable=False
                        )
                elif item.key.endswith("/") and item.key.startswith("sources/"):
                    if item.key not in seen_folders:
                        seen_folders.add(item.key)
                        folders.append(item.key)
            offset += len(page)
            if len(page) < LIST_PAGE_SIZE:
                break
    return files


def find_old_unreferenced_keys(
    database: OrmSession,
    objects: list[ListedStorageObject],
    *,
    older_than: timedelta,
    now: datetime | None = None,
) -> list[str]:
    """Find old, generated upload objects absent from authoritative evidence rows."""
    if older_than <= timedelta(0):
        raise ValueError("An explicit positive age threshold is required")
    current = now or datetime.now(UTC)
    cutoff = current - older_than
    candidates = sorted(
        {
            item.key
            for item in objects
            if item.is_file
            and GENERATED_UPLOAD_KEY.fullmatch(item.key)
            and item.created_at is not None
            and item.created_at <= cutoff
        }
    )
    if not candidates:
        return []
    referenced = set(
        database.scalars(select(Evidence.storage_key).where(Evidence.storage_key.in_(candidates)))
    )
    database.rollback()
    return [key for key in candidates if key not in referenced]


def find_missing_storage_references(
    database: OrmSession, objects: list[ListedStorageObject]
) -> list[str]:
    """Report authoritative evidence keys missing from the private object listing."""
    listed = {item.key for item in objects if item.is_file}
    query = select(Evidence.storage_key).where(
        Evidence.storage_backend == "object", Evidence.storage_key.like("sources/%")
    )
    references = list(database.scalars(query.limit(MAX_SCANNED_OBJECTS + 1)))
    database.rollback()
    if len(references) > MAX_SCANNED_OBJECTS:
        raise StorageUnavailable("Evidence consistency check exceeded its safe row limit")
    return sorted(set(references) - listed)


async def remove_verified_orphans(
    database: OrmSession, storage: SupabaseStorage, keys: list[str]
) -> tuple[list[str], list[str]]:
    """Recheck each key immediately before deletion; never delete a referenced object."""
    removed: list[str] = []
    skipped: list[str] = []
    for key in keys:
        if not GENERATED_UPLOAD_KEY.fullmatch(key):
            skipped.append(key)
            continue
        exists = database.scalar(select(Evidence.id).where(Evidence.storage_key == key))
        database.rollback()
        if exists is not None:
            skipped.append(key)
            continue
        await storage.delete(key)
        removed.append(key)
    return removed, skipped
