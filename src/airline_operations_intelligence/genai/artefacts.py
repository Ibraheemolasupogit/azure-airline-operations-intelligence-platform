"""Artefact writers for assistant outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file


def write_json(path: Path, payload: dict[str, Any]) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write deterministic JSONL and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            file.write("\n")
    return sha256_file(path)


def write_text(path: Path, content: str) -> str:
    """Write text and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def dataclass_payload(value: Any) -> Any:
    """Convert dataclass payloads to JSON-compatible dictionaries."""
    if not is_dataclass(value) or isinstance(value, type):
        return value
    return asdict(value)
