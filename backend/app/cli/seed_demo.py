"""Create deterministic, plainly synthetic records for a local UI walkthrough."""

from __future__ import annotations

import argparse
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Incident, Source
from app.db.session import get_engine

DEMO_NAMESPACE = UUID("cb3d3e47-2440-4a78-a93d-e87dd6f2ca55")
DEMO_SOURCE_ID = uuid5(DEMO_NAMESPACE, "walkthrough-source-v1")
DEMO_EVENT_ID = "demo-walkthrough-v1"
DEMO_SOURCE_NAME = "[DEMO] Synthetic walkthrough source"
DEMO_LABEL = "DEMO SAMPLE — NOT A REAL EVENT"


def seed_demo_records(session: Session) -> None:
    """Insert one labelled sample source and incident; safe to repeat."""
    source = session.get(Source, DEMO_SOURCE_ID)
    if source is None:
        source = Source(
            id=DEMO_SOURCE_ID,
            name=DEMO_SOURCE_NAME,
            source_type="simulated",
            status="ready",
            configuration={"demo": True, "fixture_version": "walkthrough-v1"},
        )
        session.add(source)
        session.flush()

    existing = session.scalar(
        select(Incident.id).where(
            Incident.source_id == DEMO_SOURCE_ID,
            Incident.source_event_id == DEMO_EVENT_ID,
        )
    )
    if existing is None:
        session.add(
            Incident(
                source_id=DEMO_SOURCE_ID,
                source_event_id=DEMO_EVENT_ID,
                detection_category=DEMO_LABEL,
                detector_name="SIMULATED_DEMO_FIXTURE",
                detector_version="walkthrough-v1",
                detector_label=DEMO_LABEL,
                detector_score=None,
                score_semantics=None,
            )
        )


def main(argv: list[str] | None = None) -> int:
    """Seed only when explicitly requested in local development or tests."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="write the synthetic demo records to the database"
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        parser.error("demo data can only be seeded when APP_ENV is development or test")
    if not args.apply:
        parser.error("pass --apply to create the explicitly synthetic demo records")

    engine = get_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        seed_demo_records(session)
    print("Local DEMO walkthrough source and sample record are ready; no real events were added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
