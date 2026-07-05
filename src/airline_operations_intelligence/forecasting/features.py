"""Leakage-safe passenger-demand feature construction."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from airline_operations_intelligence.common.exceptions import FeatureEngineeringError
from airline_operations_intelligence.forecasting.config import ForecastingConfig
from airline_operations_intelligence.forecasting.contracts import ForecastingSource, ModelRow


def build_model_table(source: ForecastingSource, config: ForecastingConfig) -> list[ModelRow]:
    """Build one modelling row per flight at the configured booking horizon."""
    schedule = _read_csv(source.processed_dir / "flight_schedule.csv")
    demand = _read_csv(source.processed_dir / "passenger_demand.csv")
    schedule_by_flight = {row["flight_id"]: row for row in schedule}
    demand_by_flight: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in demand:
        demand_by_flight[row["flight_id"]].append(row)
    rows: list[ModelRow] = []
    history_by_route: dict[str, list[ModelRow]] = defaultdict(list)
    for flight in sorted(schedule, key=lambda row: (row["operating_date"], row["flight_id"])):
        flight_id = flight["flight_id"]
        selected = _select_horizon_record(demand_by_flight.get(flight_id, []), config.settings.prediction_horizon_days)
        if selected is None:
            continue
        if flight_id not in schedule_by_flight:
            continue
        route_id = selected["route_id"]
        if config.settings.include_routes and route_id not in config.settings.include_routes:
            continue
        if route_id in config.settings.exclude_routes:
            continue
        operating_date = datetime.fromisoformat(flight["operating_date"]).date()
        observation_date = datetime.fromisoformat(selected["observation_date"]).date()
        fare_mix = json.loads(selected["fare_class_mix"])
        prior = history_by_route[route_id]
        target = float(selected[config.settings.target])
        capacity = int(selected["seat_capacity"])
        hist_mean = sum(item.target for item in prior) / len(prior) if prior else target
        hist_load = sum(item.target / item.seat_capacity for item in prior) / len(prior) if prior else target / capacity
        model_row = ModelRow(
            observation_id=f"{flight_id}:{selected['observation_date']}",
            flight_id=flight_id,
            route_id=route_id,
            operating_date=operating_date,
            observation_date=observation_date,
            days_before_departure=int(selected["days_before_departure"]),
            target=target,
            seat_capacity=capacity,
            booked_passengers=int(selected["booked_passengers"]),
            booking_velocity=float(selected["booking_velocity"]),
            cancellations_to_date=int(selected["cancellations_to_date"]),
            group_booking_count=int(selected["group_booking_count"]),
            demand_segment=selected["demand_segment"],
            discount_mix=float(fare_mix.get("discount", 0)),
            standard_mix=float(fare_mix.get("standard", 0)),
            flex_mix=float(fare_mix.get("flex", 0)),
            day_of_week=operating_date.weekday(),
            month=operating_date.month,
            weekend_flag=1 if operating_date.weekday() in {5, 6} else 0,
            historical_route_mean=hist_mean,
            historical_route_load_factor=hist_load,
            historical_route_observations=len(prior),
            features={},
            feature_availability={},
        )
        features, availability = _features(model_row, config)
        model_row = ModelRow(**{**model_row.__dict__, "features": features, "feature_availability": availability})
        history_by_route[route_id].append(model_row)
        rows.append(model_row)
    if not rows:
        raise FeatureEngineeringError("No passenger forecasting rows could be built at the configured horizon.")
    counts: dict[str, int] = defaultdict(int)
    for model_row in rows:
        counts[model_row.route_id] += 1
    return [model_row for model_row in rows if counts[model_row.route_id] >= config.settings.minimum_route_observations]


def feature_names(rows: list[ModelRow]) -> list[str]:
    """Return deterministic feature names."""
    names: set[str] = set()
    for row in rows:
        names.update(row.features)
    return sorted(names)


def feature_availability_policy(rows: list[ModelRow]) -> dict[str, str]:
    """Return feature availability policy from model rows."""
    policy: dict[str, str] = {}
    for row in rows:
        policy.update(row.feature_availability)
    return dict(sorted(policy.items()))


def _select_horizon_record(records: list[dict[str, str]], horizon: int) -> dict[str, str] | None:
    eligible = [row for row in records if int(row["days_before_departure"]) >= horizon]
    if not eligible:
        return None
    return min(eligible, key=lambda row: (int(row["days_before_departure"]) - horizon, row["observation_date"]))


def _features(row: ModelRow, config: ForecastingConfig) -> tuple[dict[str, float | str], dict[str, str]]:
    flags = config.settings.feature_flags
    features: dict[str, float | str] = {}
    availability: dict[str, str] = {}

    def add(name: str, value: float | str, policy: str) -> None:
        features[name] = value
        availability[name] = policy

    if flags["use_route"]:
        add("route_id", row.route_id, "available at schedule creation")
    if flags["use_day_of_week"]:
        add("day_of_week", float(row.day_of_week), "available at schedule creation")
    if flags["use_month"]:
        add("month", float(row.month), "available at schedule creation")
    if flags["use_days_before_departure"]:
        add("days_before_departure", float(row.days_before_departure), "available at booking-observation time")
    if flags["use_booked_passengers"]:
        add("booked_passengers", float(row.booked_passengers), "available at booking-observation time")
    if flags["use_booking_velocity"]:
        add("booking_velocity", row.booking_velocity, "available at booking-observation time")
    if flags["use_cancellations_to_date"]:
        add("cancellations_to_date", float(row.cancellations_to_date), "available at booking-observation time")
    if flags["use_group_booking_count"]:
        add("group_booking_count", float(row.group_booking_count), "available at booking-observation time")
    if flags["use_capacity"]:
        add("seat_capacity", float(row.seat_capacity), "available at schedule creation")
    if flags["use_demand_segment"]:
        add("demand_segment", row.demand_segment, "available at booking-observation time")
    if flags["use_fare_class_mix"]:
        add("fare_discount", row.discount_mix, "available at booking-observation time")
        add("fare_standard", row.standard_mix, "available at booking-observation time")
        add("fare_flex", row.flex_mix, "available at booking-observation time")
    if flags["use_historical_route_statistics"]:
        add("historical_route_mean", row.historical_route_mean, "historical aggregate available before prediction")
        add(
            "historical_route_load_factor",
            row.historical_route_load_factor,
            "historical aggregate available before prediction",
        )
        add(
            "historical_route_observations",
            float(row.historical_route_observations),
            "historical aggregate available before prediction",
        )
    add("weekend_flag", float(row.weekend_flag), "available at schedule creation")
    return features, availability


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))
