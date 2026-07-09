"""Explicit dashboard source discovery and integrity verification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import (
    DashboardCompatibilityError,
    DashboardIntegrityError,
    DashboardSourceError,
)
from airline_operations_intelligence.dashboard.artefacts import read_json
from airline_operations_intelligence.dashboard.config import DashboardConfig
from airline_operations_intelligence.dashboard.contracts import DashboardSource, SourceArtefact
from airline_operations_intelligence.data_generation.writers import sha256_file

MANIFESTS = {
    "validation": "validation-manifest.json",
    "disruption_scoring": "disruption-scoring-manifest.json",
    "monitoring": "monitoring-manifest.json",
    "passenger_forecasting": "forecast-manifest.json",
    "delay_prediction": "delay-prediction-manifest.json",
    "maintenance_analytics": "maintenance-analytics-manifest.json",
    "genai_assistant": "assistant-run-manifest.json",
}
RUN_ID_KEYS = {
    "validation": "validation_run_id",
    "disruption_scoring": "disruption_run_id",
    "monitoring": "monitoring_run_id",
    "passenger_forecasting": "forecast_run_id",
    "delay_prediction": "delay_run_id",
    "maintenance_analytics": "maintenance_run_id",
    "genai_assistant": "assistant_run_id",
}


def discover_dashboard_source(
    *,
    validation_report_dir: Path,
    disruption_report_dir: Path,
    monitoring_report_dir: Path,
    config: DashboardConfig,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    assistant_report_dir: Path | None = None,
) -> DashboardSource:
    """Discover and verify explicit dashboard input artefacts."""
    validation = _source("validation", validation_report_dir)
    if validation.manifest.get("overall_status") != "passed":
        raise DashboardSourceError(f"Validation source {validation.run_id} is not accepted.")
    disruption = _source("disruption_scoring", disruption_report_dir)
    monitoring = _source("monitoring", monitoring_report_dir)
    if config.input_options.require_disruption_input and not disruption_report_dir:
        raise DashboardSourceError("Disruption input is required.")
    if config.input_options.require_monitoring_input and not monitoring_report_dir:
        raise DashboardSourceError("Monitoring input is required.")
    _same_validation(validation.run_id, disruption)
    _same_validation(validation.run_id, monitoring)
    optional_paths = {
        "passenger_forecasting": passenger_forecast_report_dir,
        "delay_prediction": delay_prediction_report_dir,
        "maintenance_analytics": maintenance_report_dir,
        "genai_assistant": assistant_report_dir,
    }
    optional: dict[str, SourceArtefact] = {}
    for domain, path in optional_paths.items():
        if path is not None:
            artefact = _source(domain, path)
            _same_validation(validation.run_id, artefact)
            optional[domain] = artefact
    processed_dir = Path("data/processed") / validation.run_id
    if not processed_dir.is_dir():
        raise DashboardSourceError(f"Processed validation data directory not found: {processed_dir}")
    _verify_validation_processed_files(processed_dir, validation.manifest)
    if generation_run_dir is not None:
        _verify_generation_run(generation_run_dir, validation.manifest.get("source_generation_run_id"))
    return DashboardSource(
        validation=validation,
        disruption=disruption,
        monitoring=monitoring,
        optional=optional,
        generation_run_dir=generation_run_dir,
        processed_dir=processed_dir,
    )


def _source(domain: str, report_dir: Path) -> SourceArtefact:
    if not report_dir.is_dir():
        raise DashboardSourceError(f"{domain} report directory not found: {report_dir}")
    manifest_path = report_dir / MANIFESTS[domain]
    if not manifest_path.is_file():
        raise DashboardSourceError(f"{domain} manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "1.0":
        raise DashboardIntegrityError(f"Unsupported {domain} manifest schema version: {manifest.get('schema_version')}")
    run_id = _require_string(manifest, RUN_ID_KEYS[domain], domain)
    validation_run_id = manifest.get("source_validation_run_id")
    if domain == "validation":
        validation_run_id = run_id
    output_dir = _output_dir(manifest, domain, run_id)
    verified = _verify_manifest_artefacts(manifest, manifest_path.parent, output_dir)
    return SourceArtefact(
        domain=domain,
        report_dir=report_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        run_id=run_id,
        validation_run_id=str(validation_run_id) if validation_run_id is not None else None,
        manifest_sha256=sha256_file(manifest_path),
        artefact_checksums_verified=verified,
    )


def _require_string(manifest: dict[str, Any], key: str, domain: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise DashboardIntegrityError(f"{domain} manifest missing {key}.")
    return value


def _same_validation(expected: str, artefact: SourceArtefact) -> None:
    if artefact.validation_run_id != expected:
        raise DashboardCompatibilityError(
            f"{artefact.domain} validation run {artefact.validation_run_id} does not match {expected}."
        )


def _output_dir(manifest: dict[str, Any], domain: str, run_id: str) -> Path | None:
    output_dirs = manifest.get("output_dirs")
    if isinstance(output_dirs, dict):
        for key in ("outputs", "predictions"):
            value = output_dirs.get(key)
            if isinstance(value, str):
                return Path(value)
    if domain == "passenger_forecasting":
        path = manifest.get("forecast_output_path")
        if isinstance(path, str):
            candidate = Path(path)
            return candidate.parent if candidate.suffix else candidate
    if domain == "validation":
        return Path("data/processed") / run_id
    return None


def _verify_manifest_artefacts(manifest: dict[str, Any], report_dir: Path, output_dir: Path | None) -> bool:
    checksums = manifest.get("artefact_checksums")
    if not isinstance(checksums, dict):
        return False
    for name, expected in checksums.items():
        if str(name).endswith("manifest.json"):
            continue
        path = _artefact_path(str(name), report_dir, output_dir)
        if path is None or not path.is_file():
            continue
        if sha256_file(path) != expected:
            raise DashboardIntegrityError(f"Checksum mismatch for {path}.")
    return True


def _artefact_path(name: str, report_dir: Path, output_dir: Path | None) -> Path | None:
    candidates = [report_dir / name]
    if output_dir is not None:
        candidates.append(output_dir / name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _verify_validation_processed_files(processed_dir: Path, manifest: dict[str, Any]) -> None:
    checksums = manifest.get("output_file_checksums", {}).get("processed")
    if not isinstance(checksums, dict):
        raise DashboardIntegrityError("Validation manifest missing processed checksums.")
    for filename, expected in checksums.items():
        if str(filename).startswith("normalized/"):
            continue
        path = processed_dir / str(filename)
        if not path.is_file():
            raise DashboardIntegrityError(f"Processed file missing: {path}")
        if sha256_file(path) != expected:
            raise DashboardIntegrityError(f"Checksum mismatch for {path}.")


def _verify_generation_run(run_dir: Path, expected_run_id: Any) -> None:
    manifest_path = run_dir / "generation-manifest.json"
    if not manifest_path.is_file():
        raise DashboardSourceError(f"Generation manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    if expected_run_id is not None and manifest.get("run_id") != expected_run_id:
        raise DashboardCompatibilityError(
            f"Generation run {manifest.get('run_id')} does not match validation source {expected_run_id}."
        )
