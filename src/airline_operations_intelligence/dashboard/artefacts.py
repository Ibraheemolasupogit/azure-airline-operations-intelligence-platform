"""Artefact IO helpers for dashboard outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read deterministic JSONL rows."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read CSV rows as dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> str:
    """Write CSV rows with stable field ordering and return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    return sha256_file(path)


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Write JSON and return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_text(path: Path, content: str) -> str:
    """Write a text artefact and return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def csv_fieldnames(rows: list[dict[str, object]]) -> list[str]:
    """Return deterministic fieldnames from rows."""
    ordered: list[str] = []
    for row in rows:
        for key in row:
            if key not in ordered:
                ordered.append(key)
    return ordered


def count_csv(path: Path) -> int:
    """Count data rows in a CSV file."""
    return len(read_csv_rows(path))
