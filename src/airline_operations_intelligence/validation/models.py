"""Shared models for governed data validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeAlias

Scalar: TypeAlias = str | int | float | bool | None
Severity: TypeAlias = Literal["info", "warning", "error", "fatal"]
ColumnType: TypeAlias = Literal["string", "integer", "number", "boolean", "timestamp", "date", "json_string"]
FileFormat: TypeAlias = Literal["csv", "jsonl"]


@dataclass(frozen=True)
class FieldSpec:
    """Expected field contract for one source column."""

    name: str
    column_type: ColumnType
    nullable: bool = False
    enum: frozenset[str] | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class DatasetContract:
    """Validation contract for one Milestone 2 dataset."""

    filename: str
    file_format: FileFormat
    primary_key: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    foreign_keys: dict[str, str] = field(default_factory=dict)

    @property
    def field_names(self) -> list[str]:
        """Return the deterministic field order."""
        return [field_spec.name for field_spec in self.fields]


@dataclass(frozen=True)
class SourceDataset:
    """Discovered source dataset metadata from the generation manifest."""

    filename: str
    file_format: FileFormat
    row_count: int
    field_names: list[str]
    sha256: str
    primary_key: tuple[str, ...]
    foreign_keys: dict[str, str]
    path: Path


@dataclass(frozen=True)
class SourceRun:
    """A discovered and integrity-checked Milestone 2 generation run."""

    run_dir: Path
    run_id: str
    manifest: dict[str, Any]
    manifest_sha256: str
    configuration_fingerprint: str
    datasets: dict[str, SourceDataset]


@dataclass(frozen=True)
class RawRecord:
    """One parsed source record before normalization."""

    dataset: str
    row_number: int
    data: dict[str, Any]


@dataclass(frozen=True)
class NormalizedRecord:
    """One source record after conservative parsing and normalization."""

    dataset: str
    row_number: int
    data: dict[str, Scalar]


@dataclass(frozen=True)
class ValidationResult:
    """Structured validation result emitted by a rule."""

    rule_id: str
    dataset: str
    record_identifier: str | None
    field_name: str | None
    severity: Severity
    category: str
    message: str
    observed_value: str | None
    expected_condition: str
    source_file: str | None
    row_number: int | None
    passed: bool
    quarantinable: bool
    timestamp_generated_utc: str


@dataclass(frozen=True)
class DatasetValidationOutput:
    """Validated records and failures for one dataset."""

    dataset: str
    source_count: int
    valid_records: list[NormalizedRecord]
    quarantined_records: list[NormalizedRecord]
    results: list[ValidationResult]


@dataclass(frozen=True)
class ValidationRunResult:
    """Completed validation run output locations and counts."""

    validation_run_id: str
    source_run_id: str
    interim_dir: Path
    processed_dir: Path
    report_dir: Path
    manifest_path: Path
    results_path: Path
    lineage_path: Path
    metrics_path: Path
    summary_path: Path
    overall_status: str
    row_counts: dict[str, dict[str, int]]
    severity_counts: dict[str, int]
