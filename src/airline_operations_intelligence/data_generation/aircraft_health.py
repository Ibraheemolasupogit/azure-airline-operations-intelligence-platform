"""Synthetic aircraft telemetry generation."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record
from airline_operations_intelligence.data_generation.randomness import stable_id


def generate_aircraft_health(
    config: GenerationConfig,
    schedule: Dataset,
    rng: random.Random,
) -> Dataset:
    """Generate synthetic aircraft telemetry observations."""
    records: list[Record] = []
    by_aircraft: dict[str, list[Record]] = {}
    for flight in schedule.records:
        by_aircraft.setdefault(str(flight["aircraft_id"]), []).append(flight)
    for aircraft_id, flights in sorted(by_aircraft.items()):
        flights.sort(key=lambda row: str(row["scheduled_departure_utc"]))
        cycles = rng.randint(20, 180)
        hours = round(rng.uniform(40, 500), 1)
        for index, flight in enumerate(flights):
            aircraft_type = str(flight["aircraft_type"])
            departure = datetime.fromisoformat(str(flight["scheduled_departure_utc"]).replace("Z", "+00:00"))
            timestamp = departure - timedelta(minutes=35)
            ranges = config.sensor_ranges[aircraft_type]
            anomaly = rng.random() < config.settings.anomaly_rate or index == len(flights) - 1 and hours > 450
            values = {sensor: _sensor_value(bounds, rng, anomaly) for sensor, bounds in ranges.items()}
            cycles += 1
            hours += int(str(flight["scheduled_block_minutes"])) / 60
            risk = _risk_score(values, ranges, cycles, hours)
            fault_code = "SYN-DEGRADE" if anomaly and risk > 65 else ""
            records.append(
                {
                    "telemetry_id": stable_id("TEL", aircraft_id, flight["flight_id"]),
                    "aircraft_id": aircraft_id,
                    "aircraft_type": aircraft_type,
                    "event_timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
                    "flight_id": str(flight["flight_id"]),
                    "engine_1_vibration": values["engine_1_vibration"],
                    "engine_2_vibration": values["engine_2_vibration"],
                    "engine_1_temperature_c": values["engine_1_temperature_c"],
                    "engine_2_temperature_c": values["engine_2_temperature_c"],
                    "hydraulic_pressure_psi": values["hydraulic_pressure_psi"],
                    "oil_pressure_psi": values["oil_pressure_psi"],
                    "fuel_flow_kg_h": values["fuel_flow_kg_h"],
                    "brake_temperature_c": values["brake_temperature_c"],
                    "cycles_since_maintenance": cycles,
                    "flight_hours_since_maintenance": round(hours, 1),
                    "fault_code": fault_code,
                    "health_status": "review" if risk >= 70 else "watch" if risk >= 45 else "normal",
                    "maintenance_risk_score": risk,
                }
            )
    return Dataset(
        filename="aircraft_health.jsonl",
        file_format="jsonl",
        grain="one telemetry observation per aircraft and timestamp",
        primary_key="telemetry_id",
        foreign_keys={
            "aircraft_id": "fleet.aircraft_id",
            "flight_id": "flight_schedule.flight_id",
        },
        records=records,
        time_field="event_timestamp_utc",
    )


def _sensor_value(bounds: tuple[float, float], rng: random.Random, anomaly: bool) -> float:
    low, high = bounds
    if anomaly:
        value = rng.uniform(high * 0.88, high * 1.08)
    else:
        value = rng.uniform(low + (high - low) * 0.15, low + (high - low) * 0.72)
    return round(value, 2)


def _risk_score(
    values: dict[str, float],
    ranges: dict[str, tuple[float, float]],
    cycles: int,
    hours: float,
) -> float:
    pressure_penalty = 0.0
    if values["hydraulic_pressure_psi"] < ranges["hydraulic_pressure_psi"][0] * 1.15:
        pressure_penalty += 12
    if values["oil_pressure_psi"] < ranges["oil_pressure_psi"][0] * 1.15:
        pressure_penalty += 10
    high_sensor_penalty = sum(
        7
        for sensor, value in values.items()
        if value > ranges[sensor][0] + (ranges[sensor][1] - ranges[sensor][0]) * 0.82
    )
    utilisation_penalty = min(25, cycles / 20 + hours / 40)
    return round(min(100, pressure_penalty + high_sensor_penalty + utilisation_penalty), 2)
