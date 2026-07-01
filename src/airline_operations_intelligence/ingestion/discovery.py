"""Source-run discovery and generation manifest integrity checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from airline_operations_intelligence.common.exceptions import (
    SourceDiscoveryError,
    SourceIntegrityError,
    UnsupportedManifestVersionError,
)
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.validation.config import ValidationConfig
from airline_operations_intelligence.validation.models import FileFormat, SourceDataset, SourceRun
from airline_operations_intelligence.validation.schemas import REQUIRED_DATASET_NAMES, contracts_by_name

SUPPORTED_GENERATION_MANIFEST_VERSION = "1.0"


def discover_source_run(source_run_dir: Path, config: ValidationConfig) -> SourceRun:
    """Discover and validate a completed Milestone 2 source generation run."""
    run_dir = source_run_dir.resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise SourceDiscoveryError(f"Source run directory does not exist: {source_run_dir}")
    manifest_path = _safe_child(run_dir, "generation-manifest.json")
    dictionary_path = _safe_child(run_dir, "data-dictionary.json")
    summary_path = _safe_child(run_dir, "generation-summary.md")
    for required in (manifest_path, dictionary_path, summary_path):
        if not required.is_file():
            raise SourceDiscoveryError(f"Required source artefact is missing: {required}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceIntegrityError(f"Source generation manifest is not valid JSON: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise SourceIntegrityError(f"Source generation manifest must be a JSON object: {manifest_path}")
    if manifest.get("schema_version") != SUPPORTED_GENERATION_MANIFEST_VERSION:
        raise UnsupportedManifestVersionError(
            f"Unsupported generation manifest schema_version: {manifest.get('schema_version')}"
        )
    dataset_entries = manifest.get("datasets")
    if not isinstance(dataset_entries, list):
        raise SourceIntegrityError("Source generation manifest datasets must be a list.")
    contracts = contracts_by_name()
    datasets: dict[str, SourceDataset] = {}
    for entry in dataset_entries:
        dataset = _parse_dataset_entry(entry, run_dir)
        if dataset.filename in datasets:
            raise SourceIntegrityError(f"Duplicate dataset entry in generation manifest: {dataset.filename}")
        if dataset.filename not in contracts:
            if config.settings.strict_schema:
                raise SourceIntegrityError(f"Unexpected dataset in generation manifest: {dataset.filename}")
            continue
        expected = contracts[dataset.filename]
        if dataset.file_format != expected.file_format:
            raise SourceIntegrityError(f"Manifest format mismatch for {dataset.filename}: {dataset.file_format}")
        if dataset.primary_key != expected.primary_key:
            raise SourceIntegrityError(f"Manifest primary key mismatch for {dataset.filename}.")
        if dataset.foreign_keys != expected.foreign_keys:
            raise SourceIntegrityError(f"Manifest foreign key mismatch for {dataset.filename}.")
        if dataset.field_names != expected.field_names:
            raise SourceIntegrityError(f"Manifest field list mismatch for {dataset.filename}.")
        datasets[dataset.filename] = dataset
    missing = sorted(set(REQUIRED_DATASET_NAMES) - set(datasets))
    if missing:
        raise SourceDiscoveryError(f"Source run is missing required datasets: {', '.join(missing)}")
    for source in datasets.values():
        if not source.path.is_file():
            raise SourceDiscoveryError(f"Required source dataset is missing: {source.path}")
        if config.settings.verify_source_checksums and sha256_file(source.path) != source.sha256:
            raise SourceIntegrityError(f"Checksum mismatch for source dataset: {source.path}")
    return SourceRun(
        run_dir=run_dir,
        run_id=str(manifest.get("run_id", run_dir.name)),
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        configuration_fingerprint=str(manifest.get("configuration_fingerprint", "")),
        datasets=dict(sorted(datasets.items())),
    )


def _parse_dataset_entry(entry: Any, run_dir: Path) -> SourceDataset:
    if not isinstance(entry, dict):
        raise SourceIntegrityError("Source generation manifest dataset entries must be objects.")
    filename = _string(entry, "filename")
    if Path(filename).name != filename or ".." in Path(filename).parts:
        raise SourceIntegrityError(f"Unsafe source dataset filename in manifest: {filename}")
    file_format = _file_format(_string(entry, "format"))
    path = _safe_child(run_dir, filename)
    row_count = _non_negative_int(entry.get("row_count"), f"{filename}.row_count")
    field_names = _string_list(entry.get("field_names"), f"{filename}.field_names")
    primary_key = tuple(part.strip() for part in _string(entry, "primary_key").split(",") if part.strip())
    if not primary_key:
        raise SourceIntegrityError(f"Manifest primary key is empty for {filename}.")
    foreign_keys = entry.get("foreign_keys")
    if not isinstance(foreign_keys, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in foreign_keys.items()
    ):
        raise SourceIntegrityError(f"Manifest foreign_keys must be a string mapping for {filename}.")
    return SourceDataset(
        filename=filename,
        file_format=file_format,
        row_count=row_count,
        field_names=field_names,
        sha256=_string(entry, "sha256"),
        primary_key=primary_key,
        foreign_keys={str(key): str(value) for key, value in foreign_keys.items()},
        path=path,
    )


def _safe_child(run_dir: Path, filename: str) -> Path:
    candidate = (run_dir / filename).resolve()
    if run_dir not in candidate.parents and candidate != run_dir:
        raise SourceIntegrityError(f"Unsafe path escapes source run directory: {filename}")
    return candidate


def _string(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise SourceIntegrityError(f"Manifest field {key} must be a non-empty string.")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SourceIntegrityError(f"Manifest field {label} must be a list of non-empty strings.")
    return value


def _non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise SourceIntegrityError(f"Manifest field {label} must be a non-negative integer.")
    return value


def _file_format(value: str) -> FileFormat:
    if value not in {"csv", "jsonl"}:
        raise SourceIntegrityError(f"Unsupported source dataset format: {value}")
    return cast(FileFormat, value)
