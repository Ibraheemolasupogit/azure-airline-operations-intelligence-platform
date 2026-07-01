"""Deterministic dataset writers and checksum helpers."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

from airline_operations_intelligence.data_generation.models import Dataset, WrittenDataset


def write_dataset(run_dir: Path, dataset: Dataset) -> WrittenDataset:
    """Write a generated dataset and return content metadata."""
    path = run_dir / dataset.filename
    if dataset.file_format == "csv":
        _write_csv(path, dataset)
    elif dataset.file_format == "jsonl":
        _write_jsonl(path, dataset)
    else:
        raise ValueError(f"Unsupported dataset format: {dataset.file_format}")
    return WrittenDataset(
        dataset=dataset,
        path=path,
        sha256=sha256_file(path),
        row_count=len(dataset.records),
        minimum_event_time=_event_bound(dataset, minimum=True),
        maximum_event_time=_event_bound(dataset, minimum=False),
    )


def sha256_file(path: Path) -> str:
    """Return SHA-256 checksum for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, dataset: Dataset) -> None:
    field_names = dataset.field_names
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(dataset.records)


def _write_jsonl(path: Path, dataset: Dataset) -> None:
    with path.open("w", encoding="utf-8") as file:
        for record in dataset.records:
            file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            file.write("\n")


def _event_bound(dataset: Dataset, *, minimum: bool) -> datetime | None:
    if dataset.time_field is None:
        return None
    values: list[datetime] = []
    for record in dataset.records:
        raw = record.get(dataset.time_field)
        if not raw:
            continue
        values.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
    if not values:
        return None
    return min(values) if minimum else max(values)
