"""Synthetic airport operational event generation."""

from __future__ import annotations

import random
from datetime import UTC, datetime, time, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record
from airline_operations_intelligence.data_generation.randomness import stable_id

NOTE_TEMPLATES = {
    "runway_restriction": "Synthetic runway capacity constraint for planning simulation.",
    "terminal_congestion": "Synthetic passenger-flow congestion in terminal area.",
    "ground_handling_shortage": "Synthetic ground-handling resource constraint.",
    "air_traffic_flow_restriction": "Synthetic air traffic flow restriction for scenario testing.",
    "security_incident_simulation": "Synthetic security-process disruption without real incident details.",
    "equipment_outage": "Synthetic airport equipment outage affecting turnaround flow.",
    "deicing_constraint": "Synthetic deicing capacity constraint during winter operations.",
    "baggage_system_disruption": "Synthetic baggage-system disruption for operational analysis.",
}


def generate_airport_events(config: GenerationConfig, rng: random.Random) -> Dataset:
    """Generate synthetic airport operational events."""
    records: list[Record] = []
    event_types = sorted(config.airport_event_probabilities)
    for day_offset in range(config.settings.number_of_days):
        day = config.settings.start_date + timedelta(days=day_offset)
        for airport in sorted(config.airports, key=lambda item: str(item["code"])):
            airport_code = str(airport["code"])
            for event_type in event_types:
                if rng.random() > config.airport_event_probabilities[event_type]:
                    continue
                severity = min(5, max(1, rng.randint(1, 5)))
                start = datetime.combine(
                    day,
                    time(hour=rng.randint(5, 21), minute=rng.choice([0, 15, 30, 45])),
                    tzinfo=UTC,
                )
                end = start + timedelta(hours=rng.randint(1, 6))
                records.append(
                    {
                        "airport_event_id": stable_id("APT", airport_code, event_type, start.isoformat()),
                        "airport_code": airport_code,
                        "event_start_utc": start.isoformat().replace("+00:00", "Z"),
                        "event_end_utc": end.isoformat().replace("+00:00", "Z"),
                        "event_type": event_type,
                        "severity": severity,
                        "capacity_reduction_percent": min(80, severity * rng.randint(6, 11)),
                        "affected_terminal": f"T{1 + severity % 3}",
                        "affected_runway": f"RWY-{(severity * 7) % 36:02d}",
                        "estimated_delay_minutes": severity * rng.randint(6, 14),
                        "event_status": "synthetic_active",
                        "operational_notes": NOTE_TEMPLATES[event_type],
                    }
                )
    return Dataset(
        filename="airport_events.jsonl",
        file_format="jsonl",
        grain="one airport operational event per event window",
        primary_key="airport_event_id",
        foreign_keys={"airport_code": "airports.code"},
        records=records,
        time_field="event_start_utc",
    )
