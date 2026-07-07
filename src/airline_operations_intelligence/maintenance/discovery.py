"""Discovery and integrity checks for maintenance analytics sources."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import (
    MaintenanceAnalyticsIntegrityError,
    MaintenanceAnalyticsSourceError,
)
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.maintenance.config import MaintenanceAnalyticsConfig
from airline_operations_intelligence.maintenance.contracts import MaintenanceSource

REQUIRED_PROCESSED = ("aircraft_health.jsonl", "flight_schedule.csv", "delay_history.csv")
SUPPORTING_PROCESSED = ("crew_operations.csv", "weather_events.csv", "airport_events.jsonl", "passenger_demand.csv")
SUPPORTED_VALIDATION_MANIFEST_VERSION = "1.0"
REQUIRED_FIELDS = {
    "aircraft_health.jsonl": {
        "telemetry_id",
        "aircraft_id",
        "aircraft_type",
        "flight_id",
        "event_timestamp_utc",
        "engine_1_vibration",
        "engine_2_vibration",
        "engine_1_temperature_c",
        "engine_2_temperature_c",
        "hydraulic_pressure_psi",
        "oil_pressure_psi",
        "brake_temperature_c",
        "cycles_since_maintenance",
        "flight_hours_since_maintenance",
        "maintenance_risk_score",
        "health_status",
        "fault_code",
    },
    "flight_schedule.csv": {"flight_id", "aircraft_id", "route_id", "operating_date", "scheduled_departure_utc"},
    "delay_history.csv": {"flight_id", "departure_delay_minutes"},
}


def discover_maintenance_source(report_dir: Path, config: MaintenanceAnalyticsConfig) -> MaintenanceSource:
    """Load and verify a completed Milestone 3 validation run."""
    resolved_report = report_dir.resolve()
    if not resolved_report.is_dir():
        raise MaintenanceAnalyticsSourceError(f"Validation report directory does not exist: {report_dir}")
    manifest_path = _safe_child(resolved_report, "validation-manifest.json")
    lineage_path = _safe_child(resolved_report, "lineage.json")
    if not manifest_path.is_file():
        raise MaintenanceAnalyticsSourceError(f"Validation manifest not found: {manifest_path}")
    if not lineage_path.is_file():
        raise MaintenanceAnalyticsSourceError(f"Validation lineage not found: {lineage_path}")
    manifest = _load_json(manifest_path, "validation manifest")
    lineage = _load_json(lineage_path, "validation lineage")
    if manifest.get("schema_version") != SUPPORTED_VALIDATION_MANIFEST_VERSION:
        raise MaintenanceAnalyticsIntegrityError(
            f"Unsupported validation manifest version: {manifest.get('schema_version')}"
        )
    status = str(manifest.get("overall_status"))
    if status not in config.settings.accepted_validation_status:
        raise MaintenanceAnalyticsSourceError(f"Validation status {status!r} is not accepted by maintenance config.")
    if int(manifest.get("fatal_count", 0)) > 0:
        raise MaintenanceAnalyticsSourceError("Validation run contains fatal findings.")
    validation_run_id = _string(manifest, "validation_run_id")
    processed_dir = Path("data/processed") / validation_run_id
    if not processed_dir.is_dir():
        raise MaintenanceAnalyticsSourceError(f"Processed validation output directory not found: {processed_dir}")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        raise MaintenanceAnalyticsIntegrityError("validation-manifest datasets must be a list.")
    by_name = {_string(entry, "source_filename"): entry for entry in datasets if isinstance(entry, dict)}
    checksums: dict[str, str] = {}
    for filename in (*REQUIRED_PROCESSED, *SUPPORTING_PROCESSED):
        entry = by_name.get(filename)
        if entry is None:
            if filename in REQUIRED_PROCESSED:
                raise MaintenanceAnalyticsSourceError(f"Validation manifest missing required dataset: {filename}")
            continue
        path = _safe_child(processed_dir.resolve(), filename)
        if not path.is_file():
            if filename in REQUIRED_PROCESSED:
                raise MaintenanceAnalyticsSourceError(f"Processed dataset not found: {path}")
            continue
        actual = sha256_file(path)
        expected = _string(entry, "processed_sha256")
        if actual != expected:
            raise MaintenanceAnalyticsIntegrityError(f"Processed checksum mismatch for {path}")
        actual_rows = _count_jsonl(path) if filename.endswith(".jsonl") else _count_csv(path)
        if actual_rows != int(entry["valid_row_count"]):
            raise MaintenanceAnalyticsIntegrityError(f"Processed row count mismatch for {path}")
        _verify_required_fields(path, filename)
        checksums[filename] = actual
    return MaintenanceSource(
        report_dir=resolved_report,
        validation_run_id=validation_run_id,
        validation_manifest=manifest,
        validation_manifest_sha256=sha256_file(manifest_path),
        validation_lineage=lineage,
        processed_dir=processed_dir,
        processed_checksums=checksums,
    )


def _verify_required_fields(path: Path, filename: str) -> None:
    required = REQUIRED_FIELDS.get(filename)
    if not required:
        return
    if filename.endswith(".jsonl"):
        with path.open("r", encoding="utf-8") as file:
            first = json.loads(next((line for line in file if line.strip()), "{}"))
        fields = set(first)
    else:
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fields = set(reader.fieldnames or [])
    missing = required - fields
    if missing:
        raise MaintenanceAnalyticsIntegrityError(f"{filename} missing required fields: {', '.join(sorted(missing))}")


def _safe_child(root: Path, filename: str) -> Path:
    candidate = (root / filename).resolve()
    if root not in candidate.parents and candidate != root:
        raise MaintenanceAnalyticsIntegrityError(f"Unsafe path escapes allowed directory: {filename}")
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaintenanceAnalyticsIntegrityError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise MaintenanceAnalyticsIntegrityError(f"{label} must be a JSON object: {path}")
    return payload


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise MaintenanceAnalyticsIntegrityError(f"Required manifest field {key} is missing or invalid.")
    return value


def _count_csv(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as file:
        return len(list(csv.DictReader(file)))


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())
