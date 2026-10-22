import os

import pytest

from app.cli.configure_tinyfish import _write_local_key


def test_key_writer_preserves_other_settings_and_restricts_permissions(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://example\nTINYFISH_API_KEY=old-placeholder\n", encoding="utf-8"
    )
    _write_local_key(env_file, "new-secret-value")

    content = env_file.read_text(encoding="utf-8")
    assert "DATABASE_URL=postgresql://example" in content
    assert "TINYFISH_API_KEY=new-secret-value" in content
    assert "old-placeholder" not in content
    if os.name == "posix":
        assert env_file.stat().st_mode & 0o777 == 0o600


def test_key_writer_rejects_empty_multiline_and_symlink_paths(tmp_path):
    env_file = tmp_path / ".env"
    with pytest.raises(ValueError):
        _write_local_key(env_file, "\nsecret")
    with pytest.raises(ValueError):
        _write_local_key(env_file, " ")

    target = tmp_path / "target.env"
    target.write_text("KEEP=yes\n", encoding="utf-8")
    env_file.symlink_to(target)
    with pytest.raises(ValueError):
        _write_local_key(env_file, "secret")
    assert target.read_text(encoding="utf-8") == "KEEP=yes\n"
