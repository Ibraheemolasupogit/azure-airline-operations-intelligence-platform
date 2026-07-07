"""Discovery and integrity checks for disruption scoring inputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import (
    DisruptionScoringIntegrityError,
    DisruptionScoringSourceError,
)
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.disruption.config import DisruptionScoringConfig
from airline_operations_intelligence.disruption.contracts import DisruptionSource, OptionalAnalyticsSource

REQUIRED_PROCESSED = (
    "flight_schedule.csv",
    "delay_history.csv",
    "weather_events.csv",
    "airport_events.jsonl",
    "crew_operations.csv",
    "aircraft_health.jsonl",
    "passenger_demand.csv",
)
SUPPORTED_VALIDATION_MANIFEST_VERSION = "1.0"
REQUIRED_FIELDS = {
    "flight_schedule.csv": {"flight_id", "route_id", "operating_date", "scheduled_departure_utc", "aircraft_id"},
    "delay_history.csv": {
        "flight_id",
        "departure_delay_minutes",
        "arrival_delay_minutes",
        "cancelled_flag",
        "diverted_flag",
    },
    "weather_events.csv": {"airport_code", "event_start_utc", "event_end_utc", "severity", "operational_impact_score"},
    "airport_events.jsonl": {
        "airport_code",
        "event_start_utc",
        "event_end_utc",
        "severity",
        "capacity_reduction_percent",
    },
    "crew_operations.csv": {"flight_id", "captain_available", "first_officer_available", "connection_risk_minutes"},
    "aircraft_health.jsonl": {"flight_id", "aircraft_id", "event_timestamp_utc", "maintenance_risk_score"},
    "passenger_demand.csv": {"flight_id", "expected_final_passengers", "seat_capacity"},
}


def discover_disruption_source(
    *,
    report_dir: Path,
    config: DisruptionScoringConfig,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
) -> DisruptionSource:
    """Load and verify validation and optional upstream analytics sources."""
    resolved_report = report_dir.resolve()
    if not resolved_report.is_dir():
        raise DisruptionScoringSourceError(f"Validation report directory does not exist: {report_dir}")
    manifest_path = _safe_child(resolved_report, "validation-manifest.json")
    lineage_path = _safe_child(resolved_report, "lineage.json")
    manifest = _load_json(manifest_path, "validation manifest")
    lineage = _load_json(lineage_path, "validation lineage")
    if manifest.get("schema_version") != SUPPORTED_VALIDATION_MANIFEST_VERSION:
        raise DisruptionScoringIntegrityError(
            f"Unsupported validation manifest version: {manifest.get('schema_version')}"
        )
    status = str(manifest.get("overall_status"))
    if status not in config.settings.accepted_validation_status:
        raise DisruptionScoringSourceError(f"Validation status {status!r} is not accepted by disruption config.")
    if int(manifest.get("fatal_count", 0)) > 0:
        raise DisruptionScoringSourceError("Validation run contains fatal findings.")
    validation_run_id = _string(manifest, "validation_run_id")
    processed_dir = Path("data/processed") / validation_run_id
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        raise DisruptionScoringIntegrityError("validation-manifest datasets must be a list.")
    by_name = {_string(entry, "source_filename"): entry for entry in datasets if isinstance(entry, dict)}
    checksums: dict[str, str] = {}
    for filename in REQUIRED_PROCESSED:
        entry = by_name.get(filename)
        if entry is None:
            raise DisruptionScoringSourceError(f"Validation manifest missing required dataset: {filename}")
        path = _safe_child(processed_dir.resolve(), filename)
        if not path.is_file():
            raise DisruptionScoringSourceError(f"Processed dataset not found: {path}")
        actual = sha256_file(path)
        expected = _string(entry, "processed_sha256")
        if actual != expected:
            raise DisruptionScoringIntegrityError(f"Processed checksum mismatch for {path}")
        actual_rows = _count_jsonl(path) if filename.endswith(".jsonl") else _count_csv(path)
        if actual_rows != int(entry["valid_row_count"]):
            raise DisruptionScoringIntegrityError(f"Processed row count mismatch for {path}")
        _verify_required_fields(path, filename)
        checksums[filename] = actual
    passenger = (
        _optional_forecast(passenger_forecast_report_dir, validation_run_id) if passenger_forecast_report_dir else None
    )
    delay = _optional_delay(delay_prediction_report_dir, validation_run_id) if delay_prediction_report_dir else None
    maintenance = _optional_maintenance(maintenance_report_dir, validation_run_id) if maintenance_report_dir else None
    if config.settings.require_optional_inputs and not any((passenger, delay, maintenance)):
        raise DisruptionScoringSourceError("Configuration requires at least one optional analytics input.")
    return DisruptionSource(
        report_dir=resolved_report,
        validation_run_id=validation_run_id,
        validation_manifest=manifest,
        validation_manifest_sha256=sha256_file(manifest_path),
        validation_lineage=lineage,
        processed_dir=processed_dir,
        processed_checksums=checksums,
        passenger_forecast=passenger,
        delay_prediction=delay,
        maintenance_analytics=maintenance,
    )


def _optional_forecast(report_dir: Path, validation_run_id: str) -> OptionalAnalyticsSource:
    report = report_dir.resolve()
    manifest_path = _safe_child(report, "forecast-manifest.json")
    manifest = _load_json(manifest_path, "forecast manifest")
    if manifest.get("source_validation_run_id") != validation_run_id:
        raise DisruptionScoringSourceError("Passenger forecast validation run does not match disruption source.")
    run_id = _string(manifest, "forecast_run_id")
    output_path = Path("outputs/passenger_forecasting") / run_id / "passenger_forecast.csv"
    return _optional_csv_source(
        report, manifest_path, manifest, output_path, "passenger_forecast.csv", run_id, "passenger_forecast"
    )


def _optional_delay(report_dir: Path, validation_run_id: str) -> OptionalAnalyticsSource:
    report = report_dir.resolve()
    manifest_path = _safe_child(report, "delay-prediction-manifest.json")
    manifest = _load_json(manifest_path, "delay prediction manifest")
    if manifest.get("source_validation_run_id") != validation_run_id:
        raise DisruptionScoringSourceError("Delay prediction validation run does not match disruption source.")
    run_id = _string(manifest, "delay_run_id")
    output_path = Path("outputs/delay_prediction") / run_id / "delay_predictions.csv"
    return _optional_csv_source(
        report, manifest_path, manifest, output_path, "delay_predictions.csv", run_id, "delay_prediction"
    )


def _optional_maintenance(report_dir: Path, validation_run_id: str) -> OptionalAnalyticsSource:
    report = report_dir.resolve()
    manifest_path = _safe_child(report, "maintenance-analytics-manifest.json")
    manifest = _load_json(manifest_path, "maintenance manifest")
    if manifest.get("source_validation_run_id") != validation_run_id:
        raise DisruptionScoringSourceError("Maintenance analytics validation run does not match disruption source.")
    run_id = _string(manifest, "maintenance_run_id")
    output_path = Path("outputs/maintenance_analytics") / run_id / "flight_maintenance_risk.csv"
    return _optional_csv_source(
        report, manifest_path, manifest, output_path, "flight_maintenance_risk.csv", run_id, "maintenance_analytics"
    )


def _optional_csv_source(
    report: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    output_path: Path,
    filename: str,
    run_id: str,
    source_type: str,
) -> OptionalAnalyticsSource:
    if not output_path.is_file():
        raise DisruptionScoringSourceError(f"Optional analytics output not found: {output_path}")
    actual = sha256_file(output_path)
    expected = _artefact_checksum(manifest, filename)
    if expected and expected != actual:
        raise DisruptionScoringIntegrityError(f"Optional analytics checksum mismatch for {output_path}")
    rows = _read_csv(output_path)
    return OptionalAnalyticsSource(
        report_dir=report,
        run_id=run_id,
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        output_path=output_path,
        output_sha256=actual,
        rows_by_flight_id={row["flight_id"]: row for row in rows if row.get("flight_id")},
        source_type=source_type,
    )


def _artefact_checksum(manifest: dict[str, Any], filename: str) -> str | None:
    for key in ("output_artefacts", "artefact_checksums"):
        artefacts = manifest.get(key)
        if isinstance(artefacts, dict):
            value = artefacts.get(filename)
            return value if isinstance(value, str) else None
    return None


def _verify_required_fields(path: Path, filename: str) -> None:
    required = REQUIRED_FIELDS[filename]
    if filename.endswith(".jsonl"):
        with path.open("r", encoding="utf-8") as file:
            first = json.loads(next((line for line in file if line.strip()), "{}"))
        fields = set(first)
    else:
        with path.open("r", encoding="utf-8", newline="") as file:
            fields = set(csv.DictReader(file).fieldnames or [])
    missing = required - fields
    if missing:
        raise DisruptionScoringIntegrityError(f"{filename} missing required fields: {', '.join(sorted(missing))}")


def _safe_child(root: Path, filename: str) -> Path:
    candidate = (root / filename).resolve()
    if root not in candidate.parents and candidate != root:
        raise DisruptionScoringIntegrityError(f"Unsafe path escapes allowed directory: {filename}")
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DisruptionScoringIntegrityError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise DisruptionScoringIntegrityError(f"{label} must be a JSON object: {path}")
    return payload


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise DisruptionScoringIntegrityError(f"Required manifest field {key} is missing or invalid.")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _count_csv(path: Path) -> int:
    return len(_read_csv(path))


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())
