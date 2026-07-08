"""Input discovery and integrity checks for the local assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import (
    GenAIAssistantCompatibilityError,
    GenAIAssistantIntegrityError,
    GenAIAssistantSourceError,
)
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.genai.contracts import AssistantInput, AssistantSource
from airline_operations_intelligence.monitoring.manifest_readers import verify_validation_outputs

MANIFESTS = {
    "generation": "generation-manifest.json",
    "validation": "validation-manifest.json",
    "passenger_forecasting": "forecast-manifest.json",
    "delay_prediction": "delay-prediction-manifest.json",
    "maintenance_analytics": "maintenance-analytics-manifest.json",
    "disruption_scoring": "disruption-scoring-manifest.json",
    "monitoring": "monitoring-manifest.json",
}


def discover_assistant_source(
    *,
    validation_report_dir: Path,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    disruption_report_dir: Path | None = None,
    monitoring_report_dir: Path | None = None,
) -> AssistantSource:
    """Discover and verify explicit assistant source artefacts."""
    accepted: list[AssistantInput] = []
    rejected: list[AssistantInput] = []
    manifest_checksums: dict[str, str] = {}
    artefact_verified: dict[str, bool] = {}

    validation_manifest, validation_manifest_path, validation_sha = _read_manifest(validation_report_dir, "validation")
    validation_run_id = str(validation_manifest.get("validation_run_id", ""))
    if not validation_run_id:
        raise GenAIAssistantSourceError("Validation manifest is missing validation_run_id.")
    _accepted_status("validation", validation_manifest)
    verify_validation_outputs(validation_report_dir, validation_manifest)
    accepted.append(
        _input(
            "validation",
            validation_run_id,
            validation_report_dir,
            validation_manifest_path,
            validation_sha,
            True,
            "accepted",
        )
    )
    manifest_checksums["validation"] = validation_sha
    artefact_verified["validation"] = True

    generation_manifest: dict[str, Any] | None = None
    generation_run_id: str | None = None
    if generation_run_dir is not None:
        generation_manifest, generation_manifest_path, generation_sha = _read_manifest(generation_run_dir, "generation")
        generation_run_id = str(generation_manifest.get("run_id", ""))
        expected = validation_manifest.get("source_generation_run_id")
        if expected and generation_run_id != expected:
            rejected.append(
                _input(
                    "generation",
                    generation_run_id,
                    generation_run_dir,
                    generation_manifest_path,
                    generation_sha,
                    False,
                    f"expected generation run {expected}",
                )
            )
            raise GenAIAssistantCompatibilityError("Generation run does not match validation lineage.")
        _verify_generation(generation_run_dir, generation_manifest)
        accepted.append(
            _input(
                "generation",
                generation_run_id,
                generation_run_dir,
                generation_manifest_path,
                generation_sha,
                True,
                "accepted",
            )
        )
        manifest_checksums["generation"] = generation_sha
        artefact_verified["generation"] = True

    optional_dirs = {
        "passenger_forecasting": passenger_forecast_report_dir,
        "delay_prediction": delay_prediction_report_dir,
        "maintenance_analytics": maintenance_report_dir,
        "disruption_scoring": disruption_report_dir,
        "monitoring": monitoring_report_dir,
    }
    optional_manifests: dict[str, dict[str, Any]] = {}
    optional_report_dirs: dict[str, Path] = {}
    for domain, directory in optional_dirs.items():
        if directory is None:
            continue
        manifest, manifest_path, checksum = _read_manifest(directory, domain)
        run_id = _run_id(manifest, domain)
        try:
            _accepted_status(domain, manifest)
            _check_lineage(domain, manifest, validation_run_id)
            _verify_artefacts(domain, directory, manifest)
        except GenAIAssistantSourceError as exc:
            rejected.append(_input(domain, run_id, directory, manifest_path, checksum, False, str(exc)))
            raise
        optional_manifests[domain] = manifest
        optional_report_dirs[domain] = directory
        manifest_checksums[domain] = checksum
        artefact_verified[domain] = True
        accepted.append(_input(domain, run_id, directory, manifest_path, checksum, True, "accepted"))

    return AssistantSource(
        validation_run_id=validation_run_id,
        validation_report_dir=validation_report_dir,
        validation_manifest_path=validation_manifest_path,
        validation_manifest=validation_manifest,
        generation_run_id=generation_run_id,
        generation_run_dir=generation_run_dir,
        generation_manifest=generation_manifest,
        optional_manifests=optional_manifests,
        optional_report_dirs=optional_report_dirs,
        accepted_inputs=accepted,
        rejected_inputs=rejected,
        input_manifest_checksums=dict(sorted(manifest_checksums.items())),
        input_artefact_checksums_verified=dict(sorted(artefact_verified.items())),
    )


def _read_manifest(directory: Path, domain: str) -> tuple[dict[str, Any], Path, str]:
    path = directory / MANIFESTS[domain]
    if not path.exists():
        raise GenAIAssistantSourceError(f"Missing {domain} manifest: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenAIAssistantIntegrityError(f"{domain} manifest is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise GenAIAssistantIntegrityError(f"{domain} manifest root must be a mapping: {path}")
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != "1.0":
        raise GenAIAssistantIntegrityError(f"Unsupported {domain} schema version: {schema_version}")
    return payload, path, sha256_file(path)


def _accepted_status(domain: str, manifest: dict[str, Any]) -> None:
    status = str(manifest.get("overall_status", manifest.get("overall_health_status", "passed")))
    if status not in {"passed", "passed_with_warnings", "completed", "succeeded"}:
        raise GenAIAssistantSourceError(f"{domain} status {status!r} is not accepted.")


def _check_lineage(domain: str, manifest: dict[str, Any], validation_run_id: str) -> None:
    source_validation = manifest.get("source_validation_run_id")
    if source_validation != validation_run_id:
        raise GenAIAssistantCompatibilityError(
            f"{domain} source validation run {source_validation!r} does not match {validation_run_id!r}."
        )


def _verify_generation(run_dir: Path, manifest: dict[str, Any]) -> None:
    for dataset in manifest.get("datasets", []):
        path = run_dir / str(dataset["filename"])
        _verify_file(path, str(dataset["sha256"]))


def _verify_artefacts(domain: str, directory: Path, manifest: dict[str, Any]) -> None:
    if domain in {"passenger_forecasting", "delay_prediction"}:
        output_dir = (
            Path(str(manifest.get("forecast_output_path", "")))
            if domain == "passenger_forecasting"
            else _output_dir(manifest)
        )
        _verify_checksum_map(output_dir, manifest.get("output_artefacts", {}))
        _verify_checksum_map(directory, manifest.get("output_artefacts", {}))
    elif domain in {"maintenance_analytics", "disruption_scoring", "monitoring"}:
        _verify_checksum_map(_output_dir(manifest), manifest.get("artefact_checksums", {}))
        _verify_checksum_map(directory, manifest.get("artefact_checksums", {}))


def _verify_checksum_map(directory: Path, checksums: object) -> None:
    if not isinstance(checksums, dict):
        return
    for filename, checksum in checksums.items():
        if str(filename).endswith("-manifest.json") or str(filename) == "monitoring-manifest.json":
            continue
        path = directory / str(filename)
        if path.exists():
            _verify_file(path, str(checksum))


def _verify_file(path: Path, expected: str) -> None:
    if not path.exists():
        raise GenAIAssistantIntegrityError(f"Expected artefact does not exist: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise GenAIAssistantIntegrityError(f"Checksum mismatch for {path}: expected {expected}, actual {actual}")


def _output_dir(manifest: dict[str, Any]) -> Path:
    dirs = manifest.get("output_dirs")
    if isinstance(dirs, dict):
        raw = dirs.get("outputs") or dirs.get("predictions")
        if isinstance(raw, str):
            return Path(raw)
    return Path(".")


def _run_id(manifest: dict[str, Any], domain: str) -> str:
    keys = {
        "passenger_forecasting": "forecast_run_id",
        "delay_prediction": "delay_run_id",
        "maintenance_analytics": "maintenance_run_id",
        "disruption_scoring": "disruption_run_id",
        "monitoring": "monitoring_run_id",
    }
    return str(manifest.get(keys[domain], ""))


def _input(
    domain: str,
    run_id: str | None,
    path: Path,
    manifest_path: Path | None,
    checksum: str | None,
    accepted: bool,
    reason: str,
) -> AssistantInput:
    return AssistantInput(domain, run_id, path, manifest_path, checksum, accepted, reason)
