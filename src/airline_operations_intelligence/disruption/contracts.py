"""Shared contracts for disruption scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScoreBand:
    """Configured score band."""

    name: str
    minimum_score: float
    maximum_score: float


@dataclass(frozen=True)
class DisruptionSource:
    """Verified Milestone 3 source and optional upstream analytics."""

    report_dir: Path
    validation_run_id: str
    validation_manifest: dict[str, Any]
    validation_manifest_sha256: str
    validation_lineage: dict[str, Any]
    processed_dir: Path
    processed_checksums: dict[str, str]
    passenger_forecast: OptionalAnalyticsSource | None
    delay_prediction: OptionalAnalyticsSource | None
    maintenance_analytics: OptionalAnalyticsSource | None


@dataclass(frozen=True)
class OptionalAnalyticsSource:
    """Verified optional upstream analytics source."""

    report_dir: Path
    run_id: str
    manifest: dict[str, Any]
    manifest_sha256: str
    output_path: Path
    output_sha256: str
    rows_by_flight_id: dict[str, dict[str, str]]
    source_type: str


@dataclass(frozen=True)
class DisruptionFeatureRow:
    """One flight-level disruption feature row."""

    flight_id: str
    route_id: str
    operating_date: str
    scheduled_departure_utc: str
    origin_airport: str
    destination_airport: str
    aircraft_id: str
    aircraft_type: str
    features: dict[str, float | str | bool]


@dataclass(frozen=True)
class DisruptionScore:
    """Computed disruption score for one flight."""

    flight_id: str
    route_id: str
    operating_date: str
    scheduled_departure_utc: str
    origin_airport: str
    destination_airport: str
    aircraft_id: str
    component_scores: dict[str, float]
    forward_disruption_risk_score: float
    retrospective_disruption_score: float
    disruption_severity_score: float
    disruption_risk_band: str
    recovery_priority: str
    primary_disruption_driver: str
    contributing_factors: tuple[str, ...]
    recommended_review_action: str
    human_review_required: bool
    optional_passenger_forecast_used: bool
    optional_delay_prediction_used: bool
    optional_maintenance_analytics_used: bool


@dataclass(frozen=True)
class DisruptionAlert:
    """Generated disruption alert."""

    alert_id: str
    flight_id: str
    route_id: str
    operating_date: str
    origin_airport: str
    destination_airport: str
    disruption_severity_score: float
    disruption_risk_band: str
    recovery_priority: str
    primary_disruption_driver: str
    contributing_factors: tuple[str, ...]
    recommended_review_action: str
    human_review_required: bool
    evidence_fields: dict[str, float | str | bool]
    synthetic_data_warning: str


@dataclass(frozen=True)
class DisruptionRunResult:
    """Completed disruption scoring run metadata."""

    disruption_run_id: str
    source_validation_run_id: str
    output_dir: Path
    report_dir: Path
    manifest_path: Path
    scores_path: Path
    alerts_path: Path
    overall_status: str
    row_counts: dict[str, int]
