"""Deterministic random helpers."""

from __future__ import annotations

import hashlib
import random


def make_rng(seed: int, namespace: str) -> random.Random:
    """Create a deterministic random generator for a domain namespace."""
    digest = hashlib.sha256(f"{seed}:{namespace}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def stable_id(prefix: str, *parts: object, width: int = 12) -> str:
    """Create a deterministic filesystem and CSV-safe identifier."""
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:width].upper()
    return f"{prefix}-{digest}"
