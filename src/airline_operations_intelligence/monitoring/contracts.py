"""Typed contracts for local platform monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

DOMAINS = (
    "generation",
    "validation",
    "passenger_forecasting",
    "delay_prediction",
    "maintenance_analytics",
    "disruption_scoring",
)

SEVERITIES = ("info", "warning", "high", "critical")
CHECK_STATUSES = ("passed", "warning", "failed", "skipped")


@dataclass(frozen=True)
class MonitoringInput:
    """Accepted or rejected monitoring input evidence."""

    domain: str
    run_id: str | None
    path: Path
    manifest_path: Path | None
    manifest_sha256: str | None
    status: str
    accepted: bool
    reason: str


@dataclass(frozen=True)
class MonitoringSource:
    """Discovered source manifests and evidence for monitoring."""

    validation_run_id: str
    validation_report_dir: Path
    validation_manifest_path: Path
    validation_manifest: dict[str, Any]
    generation_run_id: str | None
    generation_run_dir: Path | None
    generation_manifest_path: Path | None
    generation_manifest: dict[str, Any] | None
    optional_manifests: dict[str, dict[str, Any]]
    optional_report_dirs: dict[str, Path]
    baseline_report_dir: Path | None
    baseline_manifest: dict[str, Any] | None
    accepted_inputs: list[MonitoringInput]
    rejected_inputs: list[MonitoringInput]
    input_manifest_checksums: dict[str, str]
    input_artefact_checksums_verified: dict[str, bool]


@dataclass(frozen=True)
class MonitoringMetric:
    """Single extracted monitoring metric."""

    monitoring_domain: str
    metric_name: str
    metric_value: float
    numerator: float | None
    denominator: float | None
    status: str
    severity: str
    threshold: float | None
    source_run_id: str | None
    evidence_path: str
    notes: str


@dataclass(frozen=True)
class MonitoringCheck:
    """Deterministic monitoring check result."""

    rule_id: str
    monitoring_domain: str
    status: str
    severity: str
    metric_name: str
    observed_value: float | str | None
    threshold: float | str | None
    message: str
    evidence_path: str
    remediation_hint: str
    timestamp_generated_utc: str


@dataclass(frozen=True)
class DriftComparison:
    """Metric-level drift-style comparison row."""

    monitoring_domain: str
    metric_name: str
    current_value: float | None
    baseline_value: float | None
    absolute_change: float | None
    relative_change: float | None
    threshold: float | None
    status: str
    severity: str
    notes: str


@dataclass(frozen=True)
class MonitoringAlert:
    """Monitoring alert generated from a warning or failed check."""

    monitoring_alert_id: str
    monitoring_run_id: str
    rule_id: str
    monitoring_domain: str
    severity: str
    status: str
    alert_title: str
    alert_message: str
    observed_value: float | str | None
    threshold: float | str | None
    evidence_path: str
    recommended_review_action: str
    human_review_required: bool
    synthetic_data_warning: str


@dataclass(frozen=True)
class MonitoringRunResult:
    """Result returned by the monitoring pipeline."""

    monitoring_run_id: str
    source_validation_run_id: str
    output_dir: Path
    report_dir: Path
    manifest_path: Path
    overall_status: str
    row_counts: dict[str, int]
