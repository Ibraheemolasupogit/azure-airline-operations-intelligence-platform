"""Synthetic passenger demand generation."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record


def generate_passenger_demand(
    config: GenerationConfig,
    schedule: Dataset,
    rng: random.Random,
) -> Dataset:
    """Generate booking-curve observations for every scheduled flight."""
    route_map = config.route_map
    records: list[Record] = []
    for flight in schedule.records:
        route = route_map[str(flight["route_id"])]
        departure = datetime.fromisoformat(str(flight["scheduled_departure_utc"]).replace("Z", "+00:00"))
        capacity = int(str(flight["seat_capacity"]))
        month_factor = config.demand_seasonality.get(f"{departure.month:02d}", 1.0)
        day_factor = 1.12 if departure.weekday() in {4, 6} else 0.96 if departure.weekday() == 2 else 1.0
        route_factor = float(route["popularity"])
        demand_multiplier = rng.uniform(0.62, 0.92) * route_factor * month_factor * day_factor
        expected = int(capacity * min(config.settings.max_overbooking_ratio, demand_multiplier))
        expected = max(10, min(int(capacity * config.settings.max_overbooking_ratio), expected))
        for days_before in config.settings.demand_observation_days:
            observation_date = (departure.date() - timedelta(days=days_before)).isoformat()
            curve = _booking_curve(days_before)
            booked = min(expected, int(expected * curve + rng.randint(-3, 5)))
            booked = max(0, booked)
            cancellations = min(booked, int(booked * rng.uniform(0.0, 0.035)))
            velocity = round(max(0.1, booked / max(1, 90 - days_before)), 2)
            mix = {
                "discount": round(rng.uniform(0.35, 0.62), 2),
                "standard": round(rng.uniform(0.25, 0.45), 2),
                "flex": round(rng.uniform(0.08, 0.22), 2),
            }
            records.append(
                {
                    "flight_id": str(flight["flight_id"]),
                    "observation_date": observation_date,
                    "days_before_departure": days_before,
                    "route_id": str(flight["route_id"]),
                    "booked_passengers": booked,
                    "expected_final_passengers": expected,
                    "seat_capacity": capacity,
                    "load_factor": round(expected / capacity, 4),
                    "booking_velocity": velocity,
                    "cancellations_to_date": cancellations,
                    "group_booking_count": rng.randint(0, max(1, booked // 30)),
                    "demand_segment": _segment(route_factor, departure.weekday()),
                    "fare_class_mix": json.dumps(mix, sort_keys=True, separators=(",", ":")),
                }
            )
    return Dataset(
        filename="passenger_demand.csv",
        file_format="csv",
        grain="one row per flight demand observation",
        primary_key="flight_id,observation_date",
        foreign_keys={"flight_id": "flight_schedule.flight_id", "route_id": "routes.route_id"},
        records=records,
        time_field="observation_date",
    )


def _booking_curve(days_before: int) -> float:
    if days_before >= 60:
        return 0.18
    if days_before >= 30:
        return 0.42
    if days_before >= 14:
        return 0.66
    if days_before >= 7:
        return 0.78
    return 0.93


def _segment(route_factor: float, weekday: int) -> str:
    if route_factor > 1.2 and weekday in {0, 4}:
        return "business-heavy"
    if weekday in {5, 6}:
        return "leisure-heavy"
    return "balanced"
