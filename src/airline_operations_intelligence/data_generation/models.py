"""Shared types for synthetic data generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeAlias

Scalar: TypeAlias = str | int | float | bool | None
Record: TypeAlias = dict[str, Scalar]


@dataclass(frozen=True)
class Dataset:
    """Generated dataset content before it is written to disk."""

    filename: str
    file_format: str
    grain: str
    primary_key: str
    records: list[Record]
    foreign_keys: dict[str, str]
    time_field: str | None = None

    @property
    def field_names(self) -> list[str]:
        """Return deterministic field order from the first record."""
        if not self.records:
            return []
        return list(self.records[0].keys())


@dataclass(frozen=True)
class WrittenDataset:
    """Metadata for a dataset after it has been written."""

    dataset: Dataset
    path: Path
    sha256: str
    row_count: int
    minimum_event_time: datetime | None
    maximum_event_time: datetime | None


@dataclass(frozen=True)
class GenerationResult:
    """Completed generation run metadata."""

    run_id: str
    run_dir: Path
    manifest_path: Path
    data_dictionary_path: Path
    summary_path: Path
    row_counts: dict[str, int]
