"""Manifest readers and checksum verification for monitoring inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import MonitoringIntegrityError, MonitoringSourceError
from airline_operations_intelligence.data_generation.writers import sha256_file

MANIFEST_FILENAMES = {
    "generation": "generation-manifest.json",
    "validation": "validation-manifest.json",
    "passenger_forecasting": "forecast-manifest.json",
    "delay_prediction": "delay-prediction-manifest.json",
    "maintenance_analytics": "maintenance-analytics-manifest.json",
    "disruption_scoring": "disruption-scoring-manifest.json",
    "monitoring": "monitoring-manifest.json",
}


def read_manifest(directory: Path, domain: str) -> tuple[dict[str, Any], Path, str]:
    """Read a domain manifest and return payload, path, and checksum."""
    filename = MANIFEST_FILENAMES[domain]
    path = directory / filename
    if not path.exists():
        raise MonitoringSourceError(f"Missing {domain} manifest: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MonitoringIntegrityError(f"{domain} manifest is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise MonitoringIntegrityError(f"{domain} manifest root must be a mapping: {path}")
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != "1.0":
        raise MonitoringIntegrityError(f"Unsupported {domain} manifest schema version: {schema_version}")
    return payload, path, sha256_file(path)


def verify_generation_datasets(run_dir: Path, manifest: dict[str, Any]) -> bool:
    """Verify generation dataset files against manifest row counts and checksums."""
    for dataset in manifest.get("datasets", []):
        filename = str(dataset["filename"])
        path = run_dir / filename
        _verify_file(path, str(dataset["sha256"]))
    return True


def verify_validation_outputs(report_dir: Path, manifest: dict[str, Any]) -> bool:
    """Verify validation report artefacts against manifest checksums."""
    reports = manifest.get("output_file_checksums", {}).get("reports", {})
    for filename, checksum in reports.items():
        _verify_file(report_dir / filename, str(checksum))
    processed_dir = Path("data/processed") / str(manifest.get("validation_run_id", ""))
    processed = manifest.get("output_file_checksums", {}).get("processed", {})
    for filename, checksum in processed.items():
        if "/" not in str(filename):
            _verify_file(processed_dir / filename, str(checksum))
    return True


def verify_manifest_artefacts(directory: Path, manifest: dict[str, Any], key: str) -> bool:
    """Verify artefacts listed in a manifest checksum mapping."""
    checksums = manifest.get(key, {})
    if isinstance(checksums, list):
        return True
    if not isinstance(checksums, dict):
        raise MonitoringIntegrityError(f"Manifest checksum key {key} is not a mapping.")
    for filename, checksum in checksums.items():
        if str(filename).endswith("-manifest.json"):
            continue
        path = directory / filename
        if path.exists():
            _verify_file(path, str(checksum))
    return True


def _verify_file(path: Path, expected_sha256: str) -> None:
    if not path.exists():
        raise MonitoringIntegrityError(f"Expected artefact does not exist: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise MonitoringIntegrityError(f"Checksum mismatch for {path}: expected {expected_sha256}, actual {actual}")
