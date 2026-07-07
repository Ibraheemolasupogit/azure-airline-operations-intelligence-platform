"""Shared contracts for maintenance analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MaintenanceSource:
    """Verified validation source for maintenance analytics."""

    report_dir: Path
    validation_run_id: str
    validation_manifest: dict[str, Any]
    validation_manifest_sha256: str
    validation_lineage: dict[str, Any]
    processed_dir: Path
    processed_checksums: dict[str, str]


@dataclass(frozen=True)
class HealthFeatureRow:
    """One aircraft-health feature row."""

    health_observation_id: str
    aircraft_id: str
    aircraft_type: str
    telemetry_id: str
    flight_id: str
    event_timestamp_utc: datetime
    operating_date: str
    features: dict[str, float | str | bool]
    context: dict[str, float | str | bool]


@dataclass(frozen=True)
class MaintenanceScore:
    """Maintenance risk score for one telemetry row."""

    health_observation_id: str
    aircraft_id: str
    aircraft_type: str
    telemetry_id: str
    flight_id: str
    event_timestamp_utc: datetime
    component_scores: dict[str, float]
    maintenance_risk_score: float
    aircraft_health_score: float
    risk_band: str
    alert_category: str
    top_contributing_factor: str
    contributing_factors: tuple[str, ...]
    human_review_required: bool


@dataclass(frozen=True)
class MaintenanceAlert:
    """Generated maintenance analytics alert."""

    alert_id: str
    aircraft_id: str
    aircraft_type: str
    telemetry_id: str
    flight_id: str
    event_timestamp_utc: str
    alert_category: str
    risk_band: str
    maintenance_risk_score: float
    aircraft_health_score: float
    primary_reason: str
    contributing_factors: tuple[str, ...]
    recommended_review_action: str
    evidence_fields: dict[str, float | str | bool]
    synthetic_data_warning: str
    human_review_required: bool


@dataclass(frozen=True)
class MaintenanceRunResult:
    """Completed maintenance analytics run metadata."""

    maintenance_run_id: str
    source_validation_run_id: str
    output_dir: Path
    report_dir: Path
    manifest_path: Path
    scores_path: Path
    alerts_path: Path
    overall_status: str
    row_counts: dict[str, int]
