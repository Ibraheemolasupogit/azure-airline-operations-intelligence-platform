"""Artefact writers for monitoring outputs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    """Write rows to CSV and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write rows as deterministic JSONL and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            file.write("\n")
    return sha256_file(path)


def write_json(path: Path, payload: dict[str, Any]) -> str:
    """Write JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_text(path: Path, content: str) -> str:
    """Write text and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def dataclass_rows(rows: list[Any], *, monitoring_run_id: str) -> list[dict[str, Any]]:
    """Convert dataclass rows to dictionaries with monitoring run ID first."""
    return [{"monitoring_run_id": monitoring_run_id, **asdict(row)} for row in rows]
