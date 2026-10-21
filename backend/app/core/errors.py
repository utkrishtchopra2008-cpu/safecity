"""Shared safe error primitives; endpoint-specific errors are added with API features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SafeError:
    """A safe error representation without internal exception details."""

    code: str
    message: str
