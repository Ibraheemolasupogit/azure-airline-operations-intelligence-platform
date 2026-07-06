"""Shared contracts for flight-delay prediction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PassengerForecastSource:
    """Verified optional Milestone 4 passenger forecast source."""

    report_dir: Path
    forecast_run_id: str
    manifest: dict[str, Any]
    manifest_sha256: str
    forecast_path: Path
    forecast_sha256: str
    forecasts_by_flight_id: dict[str, dict[str, str]]


@dataclass(frozen=True)
class DelayPredictionSource:
    """Verified Milestone 3 validation source for delay prediction."""

    report_dir: Path
    validation_run_id: str
    validation_manifest: dict[str, Any]
    validation_manifest_sha256: str
    validation_lineage: dict[str, Any]
    processed_dir: Path
    processed_checksums: dict[str, str]
    passenger_forecast: PassengerForecastSource | None


@dataclass(frozen=True)
class DelayModelRow:
    """One leakage-safe modelling row at scheduled-flight grain."""

    observation_id: str
    flight_id: str
    route_id: str
    origin_airport: str
    destination_airport: str
    aircraft_id: str
    aircraft_type: str
    operating_date: date
    scheduled_departure_utc: datetime
    prediction_cutoff_utc: datetime
    target: int
    delay_minutes: float
    seat_capacity: int
    departure_hour: int
    day_of_week: int
    month: int
    weather_exposure_flag: int
    airport_event_exposure_flag: int
    features: dict[str, float | str]
    feature_availability: dict[str, str]


@dataclass(frozen=True)
class PartitionedDelayRows:
    """Chronological train/validation/test delay partitions."""

    train: list[DelayModelRow]
    validation: list[DelayModelRow]
    test: list[DelayModelRow]
    boundaries: dict[str, str]


@dataclass(frozen=True)
class DelayModel:
    """A deterministic trained delay classifier."""

    model_id: str
    model_role: str
    parameters: dict[str, object]
    feature_names: list[str]
    category_levels: dict[str, list[str]]
    coefficients: dict[str, float]
    route_rates: dict[str, float]
    route_mean_delay: dict[str, float]
    global_rate: float
    global_mean_delay: float


@dataclass(frozen=True)
class DelayPrediction:
    """One probability prediction for a flight."""

    observation_id: str
    model_id: str
    model_role: str
    probability: float
    predicted_flag: int
    risk_band: str
    estimated_delay_minutes: float


@dataclass(frozen=True)
class DelayRunResult:
    """Completed delay prediction run metadata."""

    delay_run_id: str
    source_validation_run_id: str
    output_dir: Path
    model_dir: Path
    report_dir: Path
    manifest_path: Path
    predictions_path: Path
    metrics_path: Path
    champion_model_id: str
    selected_threshold: float
    overall_status: str
    partition_row_counts: dict[str, int]
