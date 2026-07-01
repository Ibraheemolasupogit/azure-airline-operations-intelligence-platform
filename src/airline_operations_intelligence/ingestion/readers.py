"""Source file readers for CSV and JSON Lines datasets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import IngestionError
from airline_operations_intelligence.validation.models import RawRecord, SourceDataset


def read_source_dataset(source: SourceDataset) -> list[RawRecord]:
    """Read a source dataset using its declared format."""
    if source.file_format == "csv":
        return _read_csv(source)
    if source.file_format == "jsonl":
        return _read_jsonl(source)
    raise IngestionError(f"Unsupported source format for {source.filename}: {source.file_format}")


def _read_csv(source: SourceDataset) -> list[RawRecord]:
    records: list[RawRecord] = []
    try:
        with source.path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise IngestionError(f"CSV source has no header: {source.path}")
            for row_number, row in enumerate(reader, start=2):
                records.append(RawRecord(dataset=source.filename, row_number=row_number, data=dict(row)))
    except csv.Error as exc:
        raise IngestionError(f"CSV source is malformed: {source.path}") from exc
    return records


def _read_jsonl(source: SourceDataset) -> list[RawRecord]:
    records: list[RawRecord] = []
    with source.path.open("r", encoding="utf-8") as file:
        for row_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                payload: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestionError(f"JSONL source is malformed at {source.path}:{row_number}") from exc
            if not isinstance(payload, dict):
                raise IngestionError(f"JSONL row must be an object at {source.path}:{row_number}")
            records.append(RawRecord(dataset=source.filename, row_number=row_number, data=payload))
    return records


def count_source_rows(path: Path, file_format: str) -> int:
    """Count rows in a source file without normalizing values."""
    if file_format == "csv":
        with path.open("r", encoding="utf-8", newline="") as file:
            return sum(1 for _ in csv.DictReader(file))
    if file_format == "jsonl":
        with path.open("r", encoding="utf-8") as file:
            return sum(1 for line in file if line.strip())
    raise IngestionError(f"Unsupported source format: {file_format}")
