"""Discovery and integrity checks for validated forecasting inputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import ForecastingIntegrityError, ForecastingSourceError
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.forecasting.config import ForecastingConfig
from airline_operations_intelligence.forecasting.contracts import ForecastingSource

REQUIRED_PROCESSED = ("passenger_demand.csv", "flight_schedule.csv")
SUPPORTED_VALIDATION_MANIFEST_VERSION = "1.0"


def discover_forecasting_source(report_dir: Path, config: ForecastingConfig) -> ForecastingSource:
    """Load and verify a completed Milestone 3 validation run."""
    resolved_report = report_dir.resolve()
    if not resolved_report.is_dir():
        raise ForecastingSourceError(f"Validation report directory does not exist: {report_dir}")
    manifest_path = _safe_child(resolved_report, "validation-manifest.json")
    lineage_path = _safe_child(resolved_report, "lineage.json")
    if not manifest_path.is_file():
        raise ForecastingSourceError(f"Validation manifest not found: {manifest_path}")
    if not lineage_path.is_file():
        raise ForecastingSourceError(f"Validation lineage not found: {lineage_path}")
    manifest = _load_json(manifest_path, "validation manifest")
    lineage = _load_json(lineage_path, "validation lineage")
    if manifest.get("schema_version") != SUPPORTED_VALIDATION_MANIFEST_VERSION:
        raise ForecastingIntegrityError(f"Unsupported validation manifest version: {manifest.get('schema_version')}")
    status = str(manifest.get("overall_status"))
    if status not in config.settings.required_validation_status:
        raise ForecastingSourceError(f"Validation status {status!r} is not accepted by forecasting configuration.")
    validation_run_id = _string(manifest, "validation_run_id")
    processed_dir = Path("data/processed") / validation_run_id
    if not processed_dir.is_dir():
        raise ForecastingSourceError(f"Processed validation output directory not found: {processed_dir}")
    checksums: dict[str, str] = {}
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        raise ForecastingIntegrityError("validation-manifest datasets must be a list.")
    by_name = {_string(entry, "source_filename"): entry for entry in datasets if isinstance(entry, dict)}
    for filename in REQUIRED_PROCESSED:
        entry = by_name.get(filename)
        if entry is None:
            raise ForecastingSourceError(f"Validation manifest missing required processed dataset: {filename}")
        path = _safe_child(processed_dir.resolve(), filename)
        if not path.is_file():
            raise ForecastingSourceError(f"Processed dataset not found: {path}")
        actual = sha256_file(path)
        expected = _string(entry, "processed_sha256")
        if actual != expected:
            raise ForecastingIntegrityError(f"Processed checksum mismatch for {path}")
        if _count_csv(path) != int(entry["valid_row_count"]):
            raise ForecastingIntegrityError(f"Processed row count mismatch for {path}")
        checksums[filename] = actual
    return ForecastingSource(
        report_dir=resolved_report,
        validation_run_id=validation_run_id,
        validation_manifest=manifest,
        validation_manifest_sha256=sha256_file(manifest_path),
        validation_lineage=lineage,
        processed_dir=processed_dir,
        processed_checksums=checksums,
    )


def _safe_child(root: Path, filename: str) -> Path:
    candidate = (root / filename).resolve()
    if root not in candidate.parents and candidate != root:
        raise ForecastingIntegrityError(f"Unsafe path escapes allowed directory: {filename}")
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ForecastingIntegrityError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ForecastingIntegrityError(f"{label} must be a JSON object: {path}")
    return payload


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ForecastingIntegrityError(f"Required manifest field {key} is missing or invalid.")
    return value


def _count_csv(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as file:
        return len(list(csv.DictReader(file)))
