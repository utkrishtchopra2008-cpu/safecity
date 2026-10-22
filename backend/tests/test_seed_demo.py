from __future__ import annotations

from unittest.mock import Mock
from uuid import UUID

import pytest

from app.cli import seed_demo


def test_seeded_records_are_explicitly_synthetic_and_have_no_score() -> None:
    session = Mock()
    session.get.return_value = None
    session.scalar.return_value = None

    seed_demo.seed_demo_records(session)

    assert session.add.call_count == 2
    source, incident = (call.args[0] for call in session.add.call_args_list)
    assert source.source_type == "simulated"
    assert source.name.startswith("[DEMO]")
    assert source.configuration["demo"] is True
    assert incident.source_event_id == seed_demo.DEMO_EVENT_ID
    assert incident.detection_category == seed_demo.DEMO_LABEL
    assert incident.detector_name == "SIMULATED_DEMO_FIXTURE"
    assert incident.detector_score is None
    assert incident.score_semantics is None


def test_seed_is_idempotent_when_deterministic_records_exist() -> None:
    session = Mock()
    session.get.return_value = object()
    session.scalar.return_value = UUID("f9850dbd-6384-42b8-9656-16481a0230ed")

    seed_demo.seed_demo_records(session)

    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_seed_command_refuses_production_before_database_access(monkeypatch) -> None:
    monkeypatch.setattr(seed_demo, "get_settings", lambda: Mock(app_env="production"))
    monkeypatch.setattr(
        seed_demo,
        "get_engine",
        lambda: pytest.fail("database must not be touched in production"),
    )

    with pytest.raises(SystemExit) as error:
        seed_demo.main(["--apply"])

    assert error.value.code == 2


def test_seed_command_requires_explicit_apply(monkeypatch) -> None:
    monkeypatch.setattr(seed_demo, "get_settings", lambda: Mock(app_env="development"))
    monkeypatch.setattr(
        seed_demo,
        "get_engine",
        lambda: pytest.fail("database must not be touched before explicit apply"),
    )

    with pytest.raises(SystemExit) as error:
        seed_demo.main([])

    assert error.value.code == 2
