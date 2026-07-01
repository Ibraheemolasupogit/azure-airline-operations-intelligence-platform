"""Generation-time invariant checks.

These checks prevent obviously corrupt generated outputs. They are intentionally not a
replacement for the governed validation pipeline planned for Milestone 3.
"""

from __future__ import annotations

from datetime import datetime

from airline_operations_intelligence.common.exceptions import GenerationInvariantError
from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset


def check_generation_invariants(config: GenerationConfig, datasets: list[Dataset]) -> None:
    """Run lightweight generation invariants across all datasets."""
    by_name = {dataset.filename: dataset for dataset in datasets}
    failures: list[str] = []
    for dataset in datasets:
        if not dataset.records:
            failures.append(f"{dataset.filename} has no rows.")
        _check_unique_primary_key(dataset, failures)

    schedule = by_name["flight_schedule.csv"]
    flight_ids = {str(row["flight_id"]) for row in schedule.records}
    aircraft_ids = set(config.fleet_map)
    airports = config.airport_codes
    route_pairs = {str(route["route_id"]): (str(route["origin"]), str(route["destination"])) for route in config.routes}
    for row in schedule.records:
        if row["origin_airport"] == row["destination_airport"]:
            failures.append("Schedule contains identical origin and destination.")
        if str(row["aircraft_id"]) not in aircraft_ids:
            failures.append(f"Schedule references unknown aircraft {row['aircraft_id']}.")
        route_pair = route_pairs[str(row["route_id"])]
        if route_pair != (row["origin_airport"], row["destination_airport"]):
            failures.append(f"Route pair mismatch for {row['flight_id']}.")
        if _parse_time(str(row["scheduled_arrival_utc"])) <= _parse_time(str(row["scheduled_departure_utc"])):
            failures.append(f"Schedule timestamp order invalid for {row['flight_id']}.")

    _check_flight_foreign_key(by_name["passenger_demand.csv"], flight_ids, failures)
    _check_flight_foreign_key(by_name["crew_operations.csv"], flight_ids, failures)
    _check_flight_foreign_key(by_name["delay_history.csv"], flight_ids, failures)
    _check_flight_foreign_key(by_name["aircraft_health.jsonl"], flight_ids, failures)

    for row in by_name["aircraft_health.jsonl"].records:
        if str(row["aircraft_id"]) not in aircraft_ids:
            failures.append(f"Telemetry references unknown aircraft {row['aircraft_id']}.")
        risk = float(str(row["maintenance_risk_score"]))
        if risk < 0 or risk > 100:
            failures.append("Maintenance risk score outside 0-100.")

    for filename in ("weather_events.csv", "airport_events.jsonl"):
        for row in by_name[filename].records:
            if str(row["airport_code"]) not in airports:
                failures.append(f"{filename} references unknown airport {row['airport_code']}.")
            if _parse_time(str(row["event_end_utc"])) <= _parse_time(str(row["event_start_utc"])):
                failures.append(f"{filename} has invalid event timestamp order.")

    for row in by_name["passenger_demand.csv"].records:
        booked = int(str(row["booked_passengers"]))
        expected = int(str(row["expected_final_passengers"]))
        capacity = int(str(row["seat_capacity"]))
        if booked > expected:
            failures.append(f"Booked passengers exceed expected final passengers for {row['flight_id']}.")
        if expected > int(capacity * config.settings.max_overbooking_ratio):
            failures.append(f"Expected passengers exceed overbooking limit for {row['flight_id']}.")
        if round(expected / capacity, 4) != float(str(row["load_factor"])):
            failures.append(f"Load factor mismatch for {row['flight_id']}.")

    if failures:
        raise GenerationInvariantError("; ".join(sorted(set(failures))))


def _check_unique_primary_key(dataset: Dataset, failures: list[str]) -> None:
    keys = dataset.primary_key.split(",")
    seen: set[tuple[str, ...]] = set()
    for row in dataset.records:
        value = tuple(str(row[key]) for key in keys)
        if value in seen:
            failures.append(f"{dataset.filename} has duplicate primary key {value}.")
        seen.add(value)


def _check_flight_foreign_key(dataset: Dataset, flight_ids: set[str], failures: list[str]) -> None:
    for row in dataset.records:
        flight_id = str(row["flight_id"])
        if flight_id and flight_id not in flight_ids:
            failures.append(f"{dataset.filename} references unknown flight {flight_id}.")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
