"""Input discovery, verification, and compatibility checks for monitoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import MonitoringCompatibilityError, MonitoringSourceError
from airline_operations_intelligence.monitoring.config import MonitoringConfig
from airline_operations_intelligence.monitoring.contracts import MonitoringInput, MonitoringSource
from airline_operations_intelligence.monitoring.manifest_readers import (
    read_manifest,
    verify_generation_datasets,
    verify_manifest_artefacts,
    verify_validation_outputs,
)

OPTIONAL_DOMAINS = {
    "passenger_forecasting": ("passenger_forecast_report_dir", "forecast_run_id"),
    "delay_prediction": ("delay_prediction_report_dir", "delay_run_id"),
    "maintenance_analytics": ("maintenance_report_dir", "maintenance_run_id"),
    "disruption_scoring": ("disruption_report_dir", "disruption_run_id"),
}


def discover_monitoring_source(
    *,
    validation_report_dir: Path,
    config: MonitoringConfig,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    disruption_report_dir: Path | None = None,
    baseline_monitoring_report_dir: Path | None = None,
) -> MonitoringSource:
    """Discover and verify explicit monitoring source artefacts."""
    accepted: list[MonitoringInput] = []
    rejected: list[MonitoringInput] = []
    manifest_checksums: dict[str, str] = {}
    artefact_verified: dict[str, bool] = {}

    validation_manifest, validation_path, validation_sha = read_manifest(validation_report_dir, "validation")
    validation_run_id = str(validation_manifest.get("validation_run_id", ""))
    if not validation_run_id:
        raise MonitoringSourceError("Validation manifest is missing validation_run_id.")
    _accept_status("validation", validation_manifest, config)
    verify_validation_outputs(validation_report_dir, validation_manifest)
    manifest_checksums["validation"] = validation_sha
    artefact_verified["validation"] = True
    accepted.append(
        _input(
            "validation", validation_run_id, validation_report_dir, validation_path, validation_sha, True, "accepted"
        )
    )

    generation_manifest: dict[str, Any] | None = None
    generation_path: Path | None = None
    generation_sha: str | None = None
    generation_run_id: str | None = None
    if generation_run_dir is not None:
        generation_manifest, generation_path, generation_sha = read_manifest(generation_run_dir, "generation")
        generation_run_id = str(generation_manifest.get("run_id", ""))
        expected = validation_manifest.get("source_generation_run_id")
        if expected and generation_run_id != expected:
            rejected.append(
                _input(
                    "generation",
                    generation_run_id,
                    generation_run_dir,
                    generation_path,
                    generation_sha,
                    False,
                    f"expected generation run {expected}",
                )
            )
            raise MonitoringCompatibilityError("Generation run does not match validation lineage.")
        verify_generation_datasets(generation_run_dir, generation_manifest)
        accepted.append(
            _input(
                "generation", generation_run_id, generation_run_dir, generation_path, generation_sha, True, "accepted"
            )
        )
        manifest_checksums["generation"] = generation_sha
        artefact_verified["generation"] = True

    optional_paths = {
        "passenger_forecasting": passenger_forecast_report_dir,
        "delay_prediction": delay_prediction_report_dir,
        "maintenance_analytics": maintenance_report_dir,
        "disruption_scoring": disruption_report_dir,
    }
    optional_manifests: dict[str, dict[str, Any]] = {}
    optional_dirs: dict[str, Path] = {}
    for domain, report_dir in optional_paths.items():
        if report_dir is None:
            continue
        manifest, manifest_path, checksum = read_manifest(report_dir, domain)
        run_id = _run_id(manifest, domain)
        try:
            _accept_status(domain, manifest, config)
            _check_validation_lineage(domain, manifest, validation_run_id)
            _verify_optional_artefacts(domain, report_dir, manifest)
        except MonitoringSourceError as exc:
            rejected.append(_input(domain, run_id, report_dir, manifest_path, checksum, False, str(exc)))
            raise
        optional_manifests[domain] = manifest
        optional_dirs[domain] = report_dir
        manifest_checksums[domain] = checksum
        artefact_verified[domain] = True
        accepted.append(_input(domain, run_id, report_dir, manifest_path, checksum, True, "accepted"))

    baseline_manifest: dict[str, Any] | None = None
    if baseline_monitoring_report_dir is not None:
        baseline_manifest, baseline_path, baseline_sha = read_manifest(baseline_monitoring_report_dir, "monitoring")
        accepted.append(
            _input(
                "baseline_monitoring",
                str(baseline_manifest.get("monitoring_run_id", "")),
                baseline_monitoring_report_dir,
                baseline_path,
                baseline_sha,
                True,
                "accepted for drift comparison",
            )
        )
        manifest_checksums["baseline_monitoring"] = baseline_sha

    return MonitoringSource(
        validation_run_id=validation_run_id,
        validation_report_dir=validation_report_dir,
        validation_manifest_path=validation_path,
        validation_manifest=validation_manifest,
        generation_run_id=generation_run_id,
        generation_run_dir=generation_run_dir,
        generation_manifest_path=generation_path,
        generation_manifest=generation_manifest,
        optional_manifests=optional_manifests,
        optional_report_dirs=optional_dirs,
        baseline_report_dir=baseline_monitoring_report_dir,
        baseline_manifest=baseline_manifest,
        accepted_inputs=accepted,
        rejected_inputs=rejected,
        input_manifest_checksums=dict(sorted(manifest_checksums.items())),
        input_artefact_checksums_verified=dict(sorted(artefact_verified.items())),
    )


def _accept_status(domain: str, manifest: dict[str, Any], config: MonitoringConfig) -> None:
    status = str(manifest.get("overall_status", manifest.get("status", "")))
    if status not in config.settings.accepted_statuses:
        raise MonitoringSourceError(f"{domain} status {status!r} is not accepted.")


def _check_validation_lineage(domain: str, manifest: dict[str, Any], validation_run_id: str) -> None:
    source_validation_run_id = manifest.get("source_validation_run_id")
    if source_validation_run_id != validation_run_id:
        raise MonitoringCompatibilityError(
            f"{domain} source validation run {source_validation_run_id!r} does not match {validation_run_id!r}."
        )


def _verify_optional_artefacts(domain: str, report_dir: Path, manifest: dict[str, Any]) -> None:
    output_dir = _output_dir(report_dir, manifest)
    if domain in {"passenger_forecasting", "delay_prediction"}:
        verify_manifest_artefacts(output_dir, manifest, "output_artefacts")
    else:
        verify_manifest_artefacts(output_dir, manifest, "artefact_checksums")
        verify_manifest_artefacts(report_dir, manifest, "artefact_checksums")


def _output_dir(report_dir: Path, manifest: dict[str, Any]) -> Path:
    dirs = manifest.get("output_dirs")
    if isinstance(dirs, dict):
        raw = dirs.get("outputs") or dirs.get("predictions")
        if isinstance(raw, str):
            return Path(raw)
    raw_output = manifest.get("forecast_output_path")
    if isinstance(raw_output, str):
        return Path(raw_output)
    return report_dir


def _run_id(manifest: dict[str, Any], domain: str) -> str:
    keys = {
        "passenger_forecasting": "forecast_run_id",
        "delay_prediction": "delay_run_id",
        "maintenance_analytics": "maintenance_run_id",
        "disruption_scoring": "disruption_run_id",
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
) -> MonitoringInput:
    return MonitoringInput(
        domain=domain,
        run_id=run_id,
        path=path,
        manifest_path=manifest_path,
        manifest_sha256=checksum,
        status="accepted" if accepted else "rejected",
        accepted=accepted,
        reason=reason,
    )
