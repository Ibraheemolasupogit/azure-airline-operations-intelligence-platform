"""Synthetic crew operations generation."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record
from airline_operations_intelligence.data_generation.randomness import stable_id


def generate_crew_operations(
    config: GenerationConfig,
    schedule: Dataset,
    weather: Dataset,
    airport_events: Dataset,
    rng: random.Random,
) -> Dataset:
    """Generate one crew assignment for every scheduled flight."""
    impacted_windows = {
        (str(record["airport_code"]), str(record["event_start_utc"])[:10])
        for record in [*weather.records, *airport_events.records]
        if float(str(record.get("operational_impact_score", record.get("estimated_delay_minutes", 0)))) > 35
    }
    records: list[Record] = []
    for flight in schedule.records:
        departure = datetime.fromisoformat(str(flight["scheduled_departure_utc"]).replace("Z", "+00:00"))
        arrival = datetime.fromisoformat(str(flight["scheduled_arrival_utc"]).replace("Z", "+00:00"))
        duty_start = departure - timedelta(minutes=75)
        duty_end = arrival + timedelta(minutes=45)
        cabin_required = max(2, int(str(flight["seat_capacity"])) // 50)
        connection_risk = rng.randint(5, 80)
        impacted = (str(flight["origin_airport"]), str(flight["operating_date"])) in impacted_windows
        reserve_used = impacted or connection_risk < 18 or rng.random() < 0.04
        disruption = reserve_used and (impacted or connection_risk < 20 or rng.random() < 0.35)
        reason = _reason(impacted, connection_risk, reserve_used)
        records.append(
            {
                "crew_assignment_id": stable_id("CREW", flight["flight_id"]),
                "flight_id": str(flight["flight_id"]),
                "crew_base": rng.choice(config.crew_bases),
                "captain_available": not (disruption and rng.random() < 0.25),
                "first_officer_available": not (disruption and rng.random() < 0.18),
                "cabin_crew_required": cabin_required,
                "cabin_crew_assigned": cabin_required if not disruption else max(0, cabin_required - 1),
                "reserve_crew_used": reserve_used,
                "duty_start_utc": duty_start.isoformat().replace("+00:00", "Z"),
                "duty_end_utc": duty_end.isoformat().replace("+00:00", "Z"),
                "duty_minutes": int((duty_end - duty_start).total_seconds() // 60),
                "connection_risk_minutes": connection_risk,
                "crew_disruption_flag": disruption,
                "crew_disruption_reason": reason if disruption else "",
            }
        )
    return Dataset(
        filename="crew_operations.csv",
        file_format="csv",
        grain="one row per crew assignment to a scheduled flight",
        primary_key="crew_assignment_id",
        foreign_keys={"flight_id": "flight_schedule.flight_id"},
        records=records,
        time_field="duty_start_utc",
    )


def _reason(impacted: bool, connection_risk: int, reserve_used: bool) -> str:
    if impacted:
        return "synthetic_weather_or_airport_disruption"
    if connection_risk < 20:
        return "synthetic_tight_inbound_connection"
    if reserve_used:
        return "synthetic_reserve_reassignment"
    return ""
