"""Shared contracts for passenger-demand forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ForecastingSource:
    """Verified Milestone 3 validation source."""

    report_dir: Path
    validation_run_id: str
    validation_manifest: dict[str, Any]
    validation_manifest_sha256: str
    validation_lineage: dict[str, Any]
    processed_dir: Path
    processed_checksums: dict[str, str]


@dataclass(frozen=True)
class ModelRow:
    """One leakage-safe modelling row."""

    observation_id: str
    flight_id: str
    route_id: str
    operating_date: date
    observation_date: date
    days_before_departure: int
    target: float
    seat_capacity: int
    booked_passengers: int
    booking_velocity: float
    cancellations_to_date: int
    group_booking_count: int
    demand_segment: str
    discount_mix: float
    standard_mix: float
    flex_mix: float
    day_of_week: int
    month: int
    weekend_flag: int
    historical_route_mean: float
    historical_route_load_factor: float
    historical_route_observations: int
    features: dict[str, float | str]
    feature_availability: dict[str, str]


@dataclass(frozen=True)
class PartitionedRows:
    """Chronological train/validation/test partitions."""

    train: list[ModelRow]
    validation: list[ModelRow]
    test: list[ModelRow]
    boundaries: dict[str, str]


@dataclass(frozen=True)
class TrainedModel:
    """A deterministic trained forecasting model."""

    model_id: str
    model_role: str
    parameters: dict[str, object]
    feature_names: list[str]
    category_levels: dict[str, list[str]]
    coefficients: dict[str, float]
    route_means: dict[str, float]
    global_mean: float
    route_conversion: dict[str, float]
    global_conversion: float


@dataclass(frozen=True)
class Prediction:
    """One model prediction for a modelling row."""

    observation_id: str
    model_id: str
    model_role: str
    raw_prediction: float
    constrained_prediction: float
    constraint_applied: bool


@dataclass(frozen=True)
class ForecastRunResult:
    """Completed passenger forecasting run metadata."""

    forecast_run_id: str
    source_validation_run_id: str
    output_dir: Path
    model_dir: Path
    report_dir: Path
    manifest_path: Path
    forecast_path: Path
    metrics_path: Path
    champion_model_id: str
    overall_status: str
    partition_row_counts: dict[str, int]
