"""Synthetic flight schedule generation."""

from __future__ import annotations

import random
from datetime import UTC, datetime, time, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record


def generate_schedule(config: GenerationConfig, rng: random.Random) -> Dataset:
    """Generate one scheduled flight leg per row."""
    records: list[Record] = []
    route_pool = _weighted_routes(config)
    fleet = sorted(config.fleet, key=lambda aircraft: str(aircraft["aircraft_id"]))
    rotations_per_aircraft = max(1, (config.settings.flights_per_day + len(fleet) - 1) // len(fleet))
    sequence = 0
    for day_offset in range(config.settings.number_of_days):
        operating_date = config.settings.start_date + timedelta(days=day_offset)
        aircraft_available = {
            str(aircraft["aircraft_id"]): datetime.combine(
                operating_date,
                time(hour=5, minute=(idx * 7) % 50),
                tzinfo=UTC,
            )
            for idx, aircraft in enumerate(fleet)
        }
        daily_count = 0
        for _rotation in range(rotations_per_aircraft):
            for aircraft in fleet:
                if daily_count >= config.settings.flights_per_day:
                    break
                sequence += 1
                daily_count += 1
                route = rng.choice(route_pool)
                aircraft_id = str(aircraft["aircraft_id"])
                aircraft_type = str(aircraft["aircraft_type"])
                block_minutes = int(str(route["scheduled_block_minutes"])) + rng.randint(-8, 12)
                scheduled_departure = aircraft_available[aircraft_id] + timedelta(minutes=rng.randint(0, 18))
                scheduled_arrival = scheduled_departure + timedelta(minutes=block_minutes)
                aircraft_available[aircraft_id] = scheduled_arrival + timedelta(minutes=45 + rng.randint(0, 20))
                type_metadata = config.aircraft_types[aircraft_type]
                records.append(
                    {
                        "flight_id": f"FLT-{operating_date:%Y%m%d}-{sequence:05d}",
                        "flight_number": f"{config.carriers[0]}{1000 + sequence % 8000}",
                        "operating_date": operating_date.isoformat(),
                        "scheduled_departure_utc": scheduled_departure.isoformat().replace("+00:00", "Z"),
                        "scheduled_arrival_utc": scheduled_arrival.isoformat().replace("+00:00", "Z"),
                        "origin_airport": str(route["origin"]),
                        "destination_airport": str(route["destination"]),
                        "route_id": str(route["route_id"]),
                        "aircraft_id": aircraft_id,
                        "aircraft_type": aircraft_type,
                        "seat_capacity": int(type_metadata["seat_capacity"]),
                        "scheduled_block_minutes": block_minutes,
                        "departure_terminal": f"T{1 + sequence % 3}",
                        "arrival_terminal": f"T{1 + (sequence + 1) % 3}",
                        "service_type": str(route.get("service_type", "scheduled")),
                        "schedule_status": "scheduled",
                    }
                )
    return Dataset(
        filename="flight_schedule.csv",
        file_format="csv",
        grain="one row per scheduled flight leg",
        primary_key="flight_id",
        foreign_keys={
            "origin_airport": "airports.code",
            "destination_airport": "airports.code",
            "aircraft_id": "fleet.aircraft_id",
            "route_id": "routes.route_id",
        },
        records=records,
        time_field="scheduled_departure_utc",
    )


def _weighted_routes(config: GenerationConfig) -> list[dict[str, object]]:
    routes: list[dict[str, object]] = []
    for route in config.routes:
        popularity = max(1, int(float(route["popularity"]) * 10))
        routes.extend([route] * popularity)
    return routes
