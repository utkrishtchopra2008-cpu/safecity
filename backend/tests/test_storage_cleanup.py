from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Evidence
from app.services.storage_cleanup import (
    find_missing_storage_references,
    find_old_unreferenced_keys,
    list_source_objects,
    remove_verified_orphans,
)
from app.storage.supabase import ListedStorageObject


def storage_key() -> str:
    return f"sources/{uuid4()}/{uuid4()}/original.mp4"


def test_storage_scan_recurses_generated_folder_tree() -> None:
    source_folder = f"sources/{uuid4()}/"
    key = f"{source_folder}{uuid4()}/original.mp4"

    class FakeStorage:
        async def list_folder(self, folder: str, *, offset: int, limit: int):
            assert offset == 0
            assert limit == 100
            if folder == "sources/":
                return [ListedStorageObject(source_folder, False, None)]
            if folder == source_folder:
                return [ListedStorageObject(key, True, datetime(2026, 10, 20, tzinfo=UTC))]
            return []

    import asyncio

    objects = asyncio.run(list_source_objects(FakeStorage()))  # type: ignore[arg-type]

    assert [item.key for item in objects] == [key]


def test_orphan_scan_only_returns_old_generated_unreferenced_objects() -> None:
    engine = create_engine("sqlite+pysqlite://")
    Evidence.__table__.create(engine)
    now = datetime(2026, 10, 23, tzinfo=UTC)
    referenced = storage_key()
    missing_reference = storage_key()
    orphan = storage_key()
    malformed = "sources/not-a-uuid/evidence/original.mp4"
    with Session(engine) as database:
        database.add_all(
            [
                Evidence(
                    source_id=uuid4(),
                    evidence_type="original_video",
                    storage_backend="object",
                    storage_key=referenced,
                    mime_type="video/mp4",
                    status="available",
                ),
                Evidence(
                    source_id=uuid4(),
                    evidence_type="original_video",
                    storage_backend="object",
                    storage_key=missing_reference,
                    mime_type="video/mp4",
                    status="available",
                ),
            ]
        )
        database.commit()
        objects = [
            ListedStorageObject(referenced, True, now - timedelta(days=5)),
            ListedStorageObject(orphan, True, now - timedelta(days=5)),
            ListedStorageObject(storage_key(), True, now - timedelta(hours=1)),
            ListedStorageObject(malformed, True, now - timedelta(days=5)),
            ListedStorageObject("sources/not-a-file/", False, None),
        ]

        result = find_old_unreferenced_keys(
            database, objects, older_than=timedelta(days=2), now=now
        )
        missing = find_missing_storage_references(database, objects)

    assert result == [orphan]
    assert missing == [missing_reference]
    engine.dispose()


def test_cleanup_rechecks_database_before_deleting() -> None:
    engine = create_engine("sqlite+pysqlite://")
    Evidence.__table__.create(engine)
    referenced = storage_key()
    orphan = storage_key()

    class FakeStorage:
        deleted: list[str] = []

        async def delete(self, key: str) -> None:
            self.deleted.append(key)

    storage = FakeStorage()
    with Session(engine) as database:
        database.add(
            Evidence(
                source_id=uuid4(),
                evidence_type="original_video",
                storage_backend="object",
                storage_key=referenced,
                mime_type="video/mp4",
                status="available",
            )
        )
        database.commit()
        import asyncio

        removed, skipped = asyncio.run(
            remove_verified_orphans(database, storage, [referenced, orphan])  # type: ignore[arg-type]
        )

    assert removed == [orphan]
    assert skipped == [referenced]
    assert storage.deleted == [orphan]
    engine.dispose()
