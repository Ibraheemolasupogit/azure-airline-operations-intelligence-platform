"""Synthetic completed flight outcome generation."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record


def generate_delay_history(
    config: GenerationConfig,
    schedule: Dataset,
    weather: Dataset,
    airport_events: Dataset,
    aircraft_health: Dataset,
    crew: Dataset,
    rng: random.Random,
) -> Dataset:
    """Generate simulated flight outcomes influenced by synthetic conditions."""
    weather_impacts = _airport_impacts(weather, "operational_impact_score")
    airport_impacts = _airport_impacts(airport_events, "estimated_delay_minutes")
    aircraft_risk = {
        str(row["flight_id"]): float(str(row["maintenance_risk_score"])) for row in aircraft_health.records
    }
    crew_risk = {
        str(row["flight_id"]): (18 if bool(row["crew_disruption_flag"]) else 0)
        + max(0, 25 - int(str(row["connection_risk_minutes"])))
        for row in crew.records
    }
    records: list[Record] = []
    reactionary_by_aircraft: dict[str, int] = {}
    alternate_airports = sorted(config.airport_codes)
    for flight in sorted(schedule.records, key=lambda row: str(row["scheduled_departure_utc"])):
        scheduled_departure = datetime.fromisoformat(str(flight["scheduled_departure_utc"]).replace("Z", "+00:00"))
        scheduled_arrival = datetime.fromisoformat(str(flight["scheduled_arrival_utc"]).replace("Z", "+00:00"))
        origin = str(flight["origin_airport"])
        destination = str(flight["destination_airport"])
        weather_score = weather_impacts.get(origin, 0.0) / 3
        airport_score = airport_impacts.get(origin, 0.0) / 4
        aircraft_score = aircraft_risk.get(str(flight["flight_id"]), 0.0) / 5
        crew_score = float(crew_risk.get(str(flight["flight_id"]), 0))
        reactionary = reactionary_by_aircraft.get(str(flight["aircraft_id"]), 0)
        departure_delay = round(
            rng.gauss(3, 9) + weather_score + airport_score + aircraft_score + crew_score + reactionary,
        )
        departure_delay = max(-8, int(departure_delay))
        cancelled = departure_delay > 105 and rng.random() < 0.18
        diverted = not cancelled and weather_score + airport_score > 35 and rng.random() < 0.05
        taxi_out = max(8, int(rng.gauss(18, 5) + airport_score / 8))
        taxi_in = max(5, int(rng.gauss(9, 3)))
        airborne = int(str(flight["scheduled_block_minutes"])) - taxi_out - taxi_in + rng.randint(-5, 8)
        arrival_delay = departure_delay + rng.randint(-8, 18) + int(weather_score / 8)
        actual_departure = None if cancelled else scheduled_departure + timedelta(minutes=departure_delay)
        actual_arrival = None if cancelled else scheduled_arrival + timedelta(minutes=arrival_delay)
        cause = _primary_cause(weather_score, airport_score, crew_score, aircraft_score, reactionary, rng)
        secondary = "reactionary" if reactionary > 15 and cause != "reactionary" else ""
        reactionary_by_aircraft[str(flight["aircraft_id"])] = max(0, min(45, arrival_delay // 3))
        diversion_airport = ""
        if diverted:
            choices = [airport for airport in alternate_airports if airport not in {origin, destination}]
            diversion_airport = rng.choice(choices)
        records.append(
            {
                "flight_id": str(flight["flight_id"]),
                "actual_departure_utc": _format_time(actual_departure),
                "actual_arrival_utc": _format_time(actual_arrival),
                "departure_delay_minutes": departure_delay,
                "arrival_delay_minutes": arrival_delay if not cancelled else "",
                "delay_category": delay_category(departure_delay),
                "primary_delay_cause": "cancelled" if cancelled else cause,
                "secondary_delay_cause": secondary,
                "taxi_out_minutes": "" if cancelled else taxi_out,
                "taxi_in_minutes": "" if cancelled else taxi_in,
                "airborne_minutes": "" if cancelled else max(15, airborne),
                "cancelled_flag": cancelled,
                "diverted_flag": diverted,
                "diversion_airport": diversion_airport,
                "reactionary_delay_minutes": reactionary,
                "weather_impact_score": round(weather_score, 2),
                "airport_impact_score": round(airport_score, 2),
                "crew_impact_score": round(crew_score, 2),
                "aircraft_impact_score": round(aircraft_score, 2),
            }
        )
    return Dataset(
        filename="delay_history.csv",
        file_format="csv",
        grain="one row per completed or simulated flight outcome",
        primary_key="flight_id",
        foreign_keys={"flight_id": "flight_schedule.flight_id", "diversion_airport": "airports.code"},
        records=records,
        time_field="actual_departure_utc",
    )


def delay_category(minutes: int) -> str:
    """Derive delay category from departure delay minutes."""
    if minutes < 0:
        return "early"
    if minutes < 15:
        return "on_time"
    if minutes < 45:
        return "minor"
    if minutes < 90:
        return "moderate"
    return "major"


def _airport_impacts(dataset: Dataset, field: str) -> dict[str, float]:
    impacts: dict[str, float] = {}
    for row in dataset.records:
        airport = str(row["airport_code"])
        impacts[airport] = max(impacts.get(airport, 0.0), float(str(row[field])))
    return impacts


def _primary_cause(
    weather: float,
    airport: float,
    crew: float,
    aircraft: float,
    reactionary: int,
    rng: random.Random,
) -> str:
    scores = {
        "weather": weather,
        "airport": airport,
        "crew": crew,
        "aircraft": aircraft,
        "reactionary": reactionary,
        "airline_operations": rng.uniform(0, 12),
    }
    return max(scores, key=lambda key: scores[key])


def _format_time(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat().replace("+00:00", "Z")
