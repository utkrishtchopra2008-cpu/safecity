"""Write a TinyFish key to the ignored local .env without echoing it."""

from __future__ import annotations

import os
import tempfile
from getpass import getpass
from pathlib import Path


def _write_local_key(env_path: Path, key: str) -> None:
    if not key.strip() or "\n" in key or "\r" in key:
        raise ValueError("A single-line nonempty key is required.")
    if env_path.is_symlink():
        raise ValueError("Refusing to write through a .env symlink.")
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = original.splitlines()
    replacement = "TINYFISH_API_KEY=" + key
    found = False
    updated: list[str] = []
    for line in lines:
        if line.startswith("TINYFISH_API_KEY="):
            if not found:
                updated.append(replacement)
                found = True
        else:
            updated.append(line)
    if not found:
        if updated and updated[-1] != "":
            updated.append("")
        updated.append(replacement)
    content = "\n".join(updated) + "\n"

    descriptor, temporary_name = tempfile.mkstemp(prefix=".env.", dir=env_path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, env_path)
        try:
            os.chmod(env_path, 0o600)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    repository_root = Path(__file__).resolve().parents[3]
    env_path = repository_root / ".env"
    key = getpass("TinyFish API key (input hidden): ").strip()
    confirmation = getpass("Confirm TinyFish API key (input hidden): ").strip()
    if key != confirmation:
        print("Keys did not match; .env was not changed.")
        return 1
    try:
        _write_local_key(env_path, key)
    except (OSError, ValueError):
        print("Could not securely configure the TinyFish key; .env was not updated.")
        return 1
    print("TINYFISH_API_KEY configured in the ignored local .env file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
