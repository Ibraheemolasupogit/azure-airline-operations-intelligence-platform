"""Discovery and integrity checks for delay prediction inputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import (
    DelayPredictionIntegrityError,
    DelayPredictionSourceError,
)
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig
from airline_operations_intelligence.delay_prediction.contracts import (
    DelayPredictionSource,
    PassengerForecastSource,
)

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


def discover_delay_prediction_source(
    report_dir: Path,
    config: DelayPredictionConfig,
    passenger_forecast_report_dir: Path | None = None,
) -> DelayPredictionSource:
    """Load and verify a completed Milestone 3 validation run and optional forecast."""
    resolved_report = report_dir.resolve()
    if not resolved_report.is_dir():
        raise DelayPredictionSourceError(f"Validation report directory does not exist: {report_dir}")
    manifest_path = _safe_child(resolved_report, "validation-manifest.json")
    lineage_path = _safe_child(resolved_report, "lineage.json")
    if not manifest_path.is_file():
        raise DelayPredictionSourceError(f"Validation manifest not found: {manifest_path}")
    if not lineage_path.is_file():
        raise DelayPredictionSourceError(f"Validation lineage not found: {lineage_path}")
    manifest = _load_json(manifest_path, "validation manifest")
    lineage = _load_json(lineage_path, "validation lineage")
    if manifest.get("schema_version") != SUPPORTED_VALIDATION_MANIFEST_VERSION:
        raise DelayPredictionIntegrityError(
            f"Unsupported validation manifest version: {manifest.get('schema_version')}"
        )
    status = str(manifest.get("overall_status"))
    if status not in config.settings.required_validation_status:
        raise DelayPredictionSourceError(f"Validation status {status!r} is not accepted by delay prediction config.")
    validation_run_id = _string(manifest, "validation_run_id")
    processed_dir = Path("data/processed") / validation_run_id
    if not processed_dir.is_dir():
        raise DelayPredictionSourceError(f"Processed validation output directory not found: {processed_dir}")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        raise DelayPredictionIntegrityError("validation-manifest datasets must be a list.")
    by_name = {_string(entry, "source_filename"): entry for entry in datasets if isinstance(entry, dict)}
    checksums: dict[str, str] = {}
    for filename in REQUIRED_PROCESSED:
        entry = by_name.get(filename)
        if entry is None:
            raise DelayPredictionSourceError(f"Validation manifest missing required dataset: {filename}")
        path = _safe_child(processed_dir.resolve(), filename)
        if not path.is_file():
            raise DelayPredictionSourceError(f"Processed dataset not found: {path}")
        actual = sha256_file(path)
        expected = _string(entry, "processed_sha256")
        if actual != expected:
            raise DelayPredictionIntegrityError(f"Processed checksum mismatch for {path}")
        expected_rows = int(entry["valid_row_count"])
        actual_rows = _count_jsonl(path) if filename.endswith(".jsonl") else _count_csv(path)
        if actual_rows != expected_rows:
            raise DelayPredictionIntegrityError(f"Processed row count mismatch for {path}")
        checksums[filename] = actual
    passenger_forecast = None
    if passenger_forecast_report_dir is not None:
        if not config.settings.allow_optional_passenger_forecast_input:
            raise DelayPredictionSourceError("Passenger forecast input is disabled by configuration.")
        passenger_forecast = _discover_passenger_forecast(passenger_forecast_report_dir, validation_run_id)
    return DelayPredictionSource(
        report_dir=resolved_report,
        validation_run_id=validation_run_id,
        validation_manifest=manifest,
        validation_manifest_sha256=sha256_file(manifest_path),
        validation_lineage=lineage,
        processed_dir=processed_dir,
        processed_checksums=checksums,
        passenger_forecast=passenger_forecast,
    )


def _discover_passenger_forecast(report_dir: Path, validation_run_id: str) -> PassengerForecastSource:
    resolved_report = report_dir.resolve()
    if not resolved_report.is_dir():
        raise DelayPredictionSourceError(f"Passenger forecast report directory does not exist: {report_dir}")
    manifest_path = _safe_child(resolved_report, "forecast-manifest.json")
    manifest = _load_json(manifest_path, "passenger forecast manifest")
    if manifest.get("source_validation_run_id") != validation_run_id:
        raise DelayPredictionSourceError(
            "Passenger forecast source validation run does not match delay validation run."
        )
    forecast_run_id = _string(manifest, "forecast_run_id")
    forecast_path = Path("outputs/passenger_forecasting") / forecast_run_id / "passenger_forecast.csv"
    if not forecast_path.is_file():
        raise DelayPredictionSourceError(f"Passenger forecast output not found: {forecast_path}")
    actual = sha256_file(forecast_path)
    expected = _artefact_checksum(manifest, "passenger_forecast.csv")
    if expected and actual != expected:
        raise DelayPredictionIntegrityError(f"Passenger forecast checksum mismatch for {forecast_path}")
    rows = _read_csv(forecast_path)
    forecasts_by_flight_id = {row["flight_id"]: row for row in rows}
    return PassengerForecastSource(
        report_dir=resolved_report,
        forecast_run_id=forecast_run_id,
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        forecast_path=forecast_path,
        forecast_sha256=actual,
        forecasts_by_flight_id=forecasts_by_flight_id,
    )


def _artefact_checksum(manifest: dict[str, Any], filename: str) -> str | None:
    artefacts = manifest.get("output_artefacts")
    if isinstance(artefacts, dict):
        value = artefacts.get(filename)
        return value if isinstance(value, str) else None
    return None


def _safe_child(root: Path, filename: str) -> Path:
    candidate = (root / filename).resolve()
    if root not in candidate.parents and candidate != root:
        raise DelayPredictionIntegrityError(f"Unsafe path escapes allowed directory: {filename}")
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DelayPredictionIntegrityError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise DelayPredictionIntegrityError(f"{label} must be a JSON object: {path}")
    return payload


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise DelayPredictionIntegrityError(f"Required manifest field {key} is missing or invalid.")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _count_csv(path: Path) -> int:
    return len(_read_csv(path))


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())
