"""Inspect or explicitly delete old Supabase objects with no evidence row."""

from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta

from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.services.storage_cleanup import (
    find_old_unreferenced_keys,
    list_source_objects,
    remove_verified_orphans,
)
from app.storage.supabase import StorageUnavailable, SupabaseStorage


def _positive_hours(value: str) -> int:
    try:
        hours = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a whole number of hours") from exc
    if not 1 <= hours <= 24 * 365:
        raise argparse.ArgumentTypeError("must be between 1 and 8760 hours")
    return hours


async def _run(*, older_than_hours: int, apply: bool) -> int:
    settings = get_settings()
    if settings.storage_backend != "supabase" or not settings.supabase_configured:
        print("Private Supabase Storage is not configured; no objects were changed.")
        return 2
    engine = get_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    storage = SupabaseStorage(settings)
    try:
        with factory() as database:
            objects = await list_source_objects(storage)
            candidates = find_old_unreferenced_keys(
                database,
                objects,
                older_than=timedelta(hours=older_than_hours),
            )
            if not apply:
                print(f"Dry run: {len(candidates)} old unreferenced upload object(s) found.")
                for key in candidates:
                    print(f"  {key}")
                print("No objects were changed. Review this list and rerun with --apply to delete.")
                return 0
            removed, skipped = await remove_verified_orphans(database, storage, candidates)
            print(f"Removed {len(removed)} verified orphan object(s); skipped {len(skipped)}.")
            for key in removed:
                print(f"  removed {key}")
        return 0
    except StorageUnavailable:
        print(
            "Storage inventory or cleanup failed safely; inspect service configuration and retry."
        )
        return 1
    finally:
        await storage.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--older-than-hours",
        type=_positive_hours,
        required=True,
        help="operator-selected minimum object age; no automatic retention threshold is assumed",
    )
    parser.add_argument(
        "--apply", action="store_true", help="delete the reviewed unreferenced objects"
    )
    args = parser.parse_args(argv)
    return asyncio.run(_run(older_than_hours=args.older_than_hours, apply=args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
