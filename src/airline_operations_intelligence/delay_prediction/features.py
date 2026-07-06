"""Leakage-safe feature construction for flight-delay prediction."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from airline_operations_intelligence.common.exceptions import DelayFeatureEngineeringError
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig
from airline_operations_intelligence.delay_prediction.contracts import DelayModelRow, DelayPredictionSource


def build_model_table(
    source: DelayPredictionSource, config: DelayPredictionConfig
) -> tuple[list[DelayModelRow], dict[str, int]]:
    """Build one modelling row per scheduled flight using only pre-cutoff fields."""
    schedule = _read_csv(source.processed_dir / "flight_schedule.csv")
    delay_by_flight = {row["flight_id"]: row for row in _read_csv(source.processed_dir / "delay_history.csv")}
    weather = _read_csv(source.processed_dir / "weather_events.csv")
    airport_events = _read_jsonl(source.processed_dir / "airport_events.jsonl")
    crew_by_flight = {row["flight_id"]: row for row in _read_csv(source.processed_dir / "crew_operations.csv")}
    health_by_flight = _health_by_flight(source.processed_dir / "aircraft_health.jsonl")
    forecast_by_flight = (
        source.passenger_forecast.forecasts_by_flight_id if source.passenger_forecast is not None else {}
    )
    exclusions: dict[str, int] = defaultdict(int)
    rows: list[DelayModelRow] = []
    history: dict[str, list[DelayModelRow]] = defaultdict(list)
    sorted_schedule = sorted(schedule, key=lambda row: (row["scheduled_departure_utc"], row["flight_id"]))
    for flight in sorted_schedule:
        flight_id = flight["flight_id"]
        delay = delay_by_flight.get(flight_id)
        if delay is None:
            exclusions["missing_delay_history"] += 1
            continue
        if config.settings.exclude_cancelled_flights and _truthy(delay["cancelled_flag"]):
            exclusions["cancelled"] += 1
            continue
        if _truthy(delay["diverted_flag"]) and not config.settings.include_diverted_flights_with_valid_departure:
            exclusions["diverted"] += 1
            continue
        if not delay["actual_departure_utc"]:
            exclusions["missing_actual_departure"] += 1
            continue
        scheduled_departure = _parse_dt(flight["scheduled_departure_utc"])
        cutoff = scheduled_departure - timedelta(minutes=config.settings.prediction_cutoff_minutes)
        departure_delay = max(0.0, float(delay["departure_delay_minutes"]))
        target = 1 if departure_delay >= config.settings.delay_threshold_minutes else 0
        route_id = flight["route_id"]
        origin = flight["origin_airport"]
        destination = flight["destination_airport"]
        operating_date = datetime.fromisoformat(flight["operating_date"]).date()
        prior_route = history[f"route:{route_id}"]
        prior_origin = history[f"origin:{origin}"]
        prior_destination = history[f"destination:{destination}"]
        prior_aircraft = history[f"aircraft:{flight['aircraft_id']}"]
        weather_features = _weather_features(weather, origin, destination, cutoff)
        airport_features = _airport_features(airport_events, origin, destination, cutoff)
        crew = crew_by_flight.get(flight_id, {})
        health = _latest_health(health_by_flight.get(flight_id, []), cutoff)
        passenger_forecast = forecast_by_flight.get(flight_id)
        base = DelayModelRow(
            observation_id=flight_id,
            flight_id=flight_id,
            route_id=route_id,
            origin_airport=origin,
            destination_airport=destination,
            aircraft_id=flight["aircraft_id"],
            aircraft_type=flight["aircraft_type"],
            operating_date=operating_date,
            scheduled_departure_utc=scheduled_departure,
            prediction_cutoff_utc=cutoff,
            target=target,
            delay_minutes=departure_delay,
            seat_capacity=int(flight["seat_capacity"]),
            departure_hour=scheduled_departure.hour,
            day_of_week=operating_date.weekday(),
            month=operating_date.month,
            weather_exposure_flag=1 if weather_features["weather_event_count"] else 0,
            airport_event_exposure_flag=1 if airport_features["airport_event_count"] else 0,
            features={},
            feature_availability={},
        )
        features, availability = _features(
            base,
            flight,
            crew,
            health,
            passenger_forecast,
            weather_features,
            airport_features,
            {
                "route": _historical(prior_route),
                "origin": _historical(prior_origin),
                "destination": _historical(prior_destination),
                "aircraft": _historical(prior_aircraft),
            },
            config,
        )
        model_row = DelayModelRow(**{**base.__dict__, "features": features, "feature_availability": availability})
        history[f"route:{route_id}"].append(model_row)
        history[f"origin:{origin}"].append(model_row)
        history[f"destination:{destination}"].append(model_row)
        history[f"aircraft:{flight['aircraft_id']}"].append(model_row)
        rows.append(model_row)
    if not rows:
        raise DelayFeatureEngineeringError("No delay prediction rows could be built from the validated source.")
    exclusions["modelled_rows"] = len(rows)
    exclusions["source_schedule_rows"] = len(schedule)
    return rows, dict(sorted(exclusions.items()))


def feature_names(rows: list[DelayModelRow]) -> list[str]:
    """Return deterministic feature names."""
    names: set[str] = set()
    for row in rows:
        names.update(row.features)
    return sorted(names)


def feature_availability_policy(rows: list[DelayModelRow]) -> dict[str, str]:
    """Return feature availability policy from rows."""
    policy: dict[str, str] = {}
    for row in rows:
        policy.update(row.feature_availability)
    return dict(sorted(policy.items()))


def _features(
    row: DelayModelRow,
    flight: dict[str, str],
    crew: dict[str, str],
    health: dict[str, object] | None,
    passenger_forecast: dict[str, str] | None,
    weather: dict[str, float],
    airport: dict[str, float],
    historical: dict[str, dict[str, float]],
    config: DelayPredictionConfig,
) -> tuple[dict[str, float | str], dict[str, str]]:
    flags = config.settings.feature_flags
    features: dict[str, float | str] = {}
    availability: dict[str, str] = {}

    def add(name: str, value: float | str, policy: str) -> None:
        features[name] = value
        availability[name] = policy

    if flags["use_route"]:
        add("route_id", row.route_id, "available at schedule creation")
    if flags["use_origin_airport"]:
        add("origin_airport", row.origin_airport, "available at schedule creation")
    if flags["use_destination_airport"]:
        add("destination_airport", row.destination_airport, "available at schedule creation")
    if flags["use_aircraft_type"]:
        add("aircraft_type", row.aircraft_type, "available at schedule creation")
    if flags["use_seat_capacity"]:
        add("seat_capacity", float(row.seat_capacity), "available at schedule creation")
    if flags["use_scheduled_block_minutes"]:
        add("scheduled_block_minutes", float(flight["scheduled_block_minutes"]), "available at schedule creation")
    if flags["use_departure_hour"]:
        add("departure_hour", float(row.departure_hour), "available at schedule creation")
    if flags["use_day_of_week"]:
        add("day_of_week", float(row.day_of_week), "available at schedule creation")
    if flags["use_month"]:
        add("month", float(row.month), "available at schedule creation")
    if flags["use_weekend_flag"]:
        add("weekend_flag", 1.0 if row.day_of_week in {5, 6} else 0.0, "available at schedule creation")
    if flags["use_service_type"]:
        add("service_type", flight["service_type"], "available at schedule creation")
    if flags["use_schedule_status"]:
        add("schedule_status", flight["schedule_status"], "available at schedule creation")
    if flags["use_predeparture_weather"]:
        for name, value in weather.items():
            add(name, value, "weather events started before or at prediction cutoff")
    if flags["use_predeparture_airport_events"]:
        for name, value in airport.items():
            add(name, value, "airport events started before or at prediction cutoff")
    if flags["use_predeparture_crew_state"] and crew:
        add("captain_available", _float_bool(crew["captain_available"]), "crew roster state available before cutoff")
        add(
            "first_officer_available",
            _float_bool(crew["first_officer_available"]),
            "crew roster state available before cutoff",
        )
        add(
            "cabin_crew_gap",
            float(crew["cabin_crew_required"]) - float(crew["cabin_crew_assigned"]),
            "crew roster state available before cutoff",
        )
        add("reserve_crew_used", _float_bool(crew["reserve_crew_used"]), "crew roster state available before cutoff")
        add(
            "connection_risk_minutes",
            float(crew["connection_risk_minutes"]),
            "crew connection risk known before cutoff",
        )
    if flags["use_predeparture_aircraft_health"] and health:
        add(
            "maintenance_risk_score",
            _object_float(health["maintenance_risk_score"]),
            "latest telemetry at or before cutoff",
        )
        add(
            "cycles_since_maintenance",
            _object_float(health["cycles_since_maintenance"]),
            "latest telemetry at or before cutoff",
        )
        add(
            "flight_hours_since_maintenance",
            _object_float(health["flight_hours_since_maintenance"]),
            "latest telemetry at or before cutoff",
        )
        add("aircraft_health_status", str(health["health_status"]), "latest telemetry at or before cutoff")
    if flags["use_historical_route_delay_features"]:
        add("historical_route_delay_rate", historical["route"]["rate"], "prior flights only")
        add("historical_route_mean_delay", historical["route"]["mean_delay"], "prior flights only")
        add("historical_route_observations", historical["route"]["count"], "prior flights only")
    if flags["use_historical_airport_delay_features"]:
        add("historical_origin_delay_rate", historical["origin"]["rate"], "prior flights only")
        add("historical_destination_delay_rate", historical["destination"]["rate"], "prior flights only")
    if flags["use_historical_aircraft_delay_features"]:
        add("historical_aircraft_delay_rate", historical["aircraft"]["rate"], "prior flights only")
    if flags["use_optional_passenger_forecast"] and passenger_forecast is not None:
        forecast_passengers = float(passenger_forecast["forecast_passengers"])
        add("forecast_passengers", forecast_passengers, "Milestone 4 forecast value only")
        add("forecast_load_factor", forecast_passengers / max(1, row.seat_capacity), "Milestone 4 forecast value only")
        if passenger_forecast.get("forecast_upper_95") and passenger_forecast.get("forecast_lower_95"):
            add(
                "forecast_uncertainty_width_95",
                float(passenger_forecast["forecast_upper_95"]) - float(passenger_forecast["forecast_lower_95"]),
                "Milestone 4 forecast interval only",
            )
        add(
            "forecast_constraint_applied",
            _float_bool(passenger_forecast["constraint_applied"]),
            "Milestone 4 forecast metadata only",
        )
    return features, availability


def _historical(rows: list[DelayModelRow]) -> dict[str, float]:
    if not rows:
        return {"rate": 0.5, "mean_delay": 0.0, "count": 0.0}
    return {
        "rate": sum(row.target for row in rows) / len(rows),
        "mean_delay": sum(row.delay_minutes for row in rows) / len(rows),
        "count": float(len(rows)),
    }


def _weather_features(
    events: list[dict[str, str]], origin: str, destination: str, cutoff: datetime
) -> dict[str, float]:
    eligible = [
        row
        for row in events
        if row["airport_code"] in {origin, destination}
        and _parse_dt(row["event_start_utc"]) <= cutoff
        and _parse_dt(row["event_end_utc"]) >= cutoff
    ]
    return {
        "weather_event_count": float(len(eligible)),
        "weather_max_severity": max((float(row["severity"]) for row in eligible), default=0.0),
        "weather_max_impact_score": max((float(row["operational_impact_score"]) for row in eligible), default=0.0),
    }


def _airport_features(
    events: list[dict[str, object]], origin: str, destination: str, cutoff: datetime
) -> dict[str, float]:
    eligible = [
        row
        for row in events
        if row["airport_code"] in {origin, destination}
        and _parse_dt(str(row["event_start_utc"])) <= cutoff
        and _parse_dt(str(row["event_end_utc"])) >= cutoff
    ]
    return {
        "airport_event_count": float(len(eligible)),
        "airport_max_severity": max((_object_float(row["severity"]) for row in eligible), default=0.0),
        "airport_max_capacity_reduction": max(
            (_object_float(row["capacity_reduction_percent"]) for row in eligible), default=0.0
        ),
    }


def _health_by_flight(path: Path) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in _read_jsonl(path):
        grouped[str(row["flight_id"])].append(row)
    return grouped


def _latest_health(rows: list[dict[str, object]], cutoff: datetime) -> dict[str, object] | None:
    eligible = [row for row in rows if _parse_dt(str(row["event_timestamp_utc"])) <= cutoff]
    if not eligible:
        return None
    return max(eligible, key=lambda row: str(row["event_timestamp_utc"]))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _truthy(value: str) -> bool:
    return value.lower() == "true"


def _float_bool(value: str) -> float:
    return 1.0 if _truthy(str(value)) else 0.0


def _object_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
