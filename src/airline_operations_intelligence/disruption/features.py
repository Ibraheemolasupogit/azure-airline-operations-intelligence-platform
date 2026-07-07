"""Feature construction for operational disruption scoring."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from airline_operations_intelligence.common.exceptions import DisruptionFeatureEngineeringError
from airline_operations_intelligence.disruption.contracts import DisruptionFeatureRow, DisruptionSource
from airline_operations_intelligence.disruption.dataset import read_csv, read_jsonl


def build_disruption_features(source: DisruptionSource) -> list[DisruptionFeatureRow]:
    """Build one disruption feature row per scheduled flight."""
    schedule = read_csv(source.processed_dir / "flight_schedule.csv")
    delay_by_flight = {row["flight_id"]: row for row in read_csv(source.processed_dir / "delay_history.csv")}
    crew_by_flight = {row["flight_id"]: row for row in read_csv(source.processed_dir / "crew_operations.csv")}
    weather = read_csv(source.processed_dir / "weather_events.csv")
    airport_events = read_jsonl(source.processed_dir / "airport_events.jsonl")
    demand_by_flight = _latest_demand(read_csv(source.processed_dir / "passenger_demand.csv"))
    health_by_flight = _latest_health(read_jsonl(source.processed_dir / "aircraft_health.jsonl"))
    history: dict[str, list[DisruptionFeatureRow]] = defaultdict(list)
    rows: list[DisruptionFeatureRow] = []
    for flight in sorted(schedule, key=lambda row: (row["scheduled_departure_utc"], row["flight_id"])):
        flight_id = flight["flight_id"]
        delay = delay_by_flight.get(flight_id, {})
        crew = crew_by_flight.get(flight_id, {})
        demand = demand_by_flight.get(flight_id, {})
        health = health_by_flight.get(flight_id, {})
        scheduled_departure = _parse_dt(flight["scheduled_departure_utc"])
        route_history = history[flight["route_id"]]
        weather_features = _weather_features(
            weather, flight["origin_airport"], flight["destination_airport"], scheduled_departure
        )
        airport_features = _airport_features(
            airport_events, flight["origin_airport"], flight["destination_airport"], scheduled_departure
        )
        optional_forecast = (
            source.passenger_forecast.rows_by_flight_id.get(flight_id) if source.passenger_forecast else None
        )
        optional_delay = source.delay_prediction.rows_by_flight_id.get(flight_id) if source.delay_prediction else None
        optional_maintenance = (
            source.maintenance_analytics.rows_by_flight_id.get(flight_id) if source.maintenance_analytics else None
        )
        features: dict[str, float | str | bool] = {
            "disruption_observation_id": flight_id,
            "flight_number": flight["flight_number"],
            "seat_capacity": _float(flight["seat_capacity"]),
            "service_type": flight["service_type"],
            "schedule_status": flight["schedule_status"],
            "departure_delay_minutes": _float(delay.get("departure_delay_minutes", 0.0)),
            "arrival_delay_minutes": _float(delay.get("arrival_delay_minutes", 0.0)),
            "delay_category": str(delay.get("delay_category", "")),
            "cancelled_flag": _truthy(str(delay.get("cancelled_flag", "False"))),
            "diverted_flag": _truthy(str(delay.get("diverted_flag", "False"))),
            "reactionary_delay_minutes": _float(delay.get("reactionary_delay_minutes", 0.0)),
            "delay_outcome_available": bool(delay),
            "prior_route_delay_pressure": _prior_delay_pressure(route_history),
            "same_day_route_disruption_count": _same_day_route_count(route_history, flight["operating_date"]),
            "captain_available": _truthy(str(crew.get("captain_available", "True"))),
            "first_officer_available": _truthy(str(crew.get("first_officer_available", "True"))),
            "cabin_crew_required": _float(crew.get("cabin_crew_required", 0.0)),
            "cabin_crew_assigned": _float(crew.get("cabin_crew_assigned", 0.0)),
            "reserve_crew_used": _truthy(str(crew.get("reserve_crew_used", "False"))),
            "connection_risk_minutes": _float(crew.get("connection_risk_minutes", 0.0)),
            "crew_disruption_flag": _truthy(str(crew.get("crew_disruption_flag", "False"))),
            "crew_shortage_flag": _float(crew.get("cabin_crew_assigned", 0.0))
            < _float(crew.get("cabin_crew_required", 0.0)),
            "expected_final_passengers": _float(demand.get("expected_final_passengers", 0.0)),
            "latest_booking_load_factor": _float(demand.get("expected_final_passengers", 0.0))
            / max(1.0, _float(flight["seat_capacity"])),
            "source_maintenance_risk_score": _float(health.get("maintenance_risk_score", 0.0)) / 100.0,
            **weather_features,
            **airport_features,
            **_optional_forecast_features(optional_forecast, flight),
            **_optional_delay_features(optional_delay),
            **_optional_maintenance_features(optional_maintenance),
        }
        features.update(_context_flags(features))
        row = DisruptionFeatureRow(
            flight_id=flight_id,
            route_id=flight["route_id"],
            operating_date=flight["operating_date"],
            scheduled_departure_utc=flight["scheduled_departure_utc"],
            origin_airport=flight["origin_airport"],
            destination_airport=flight["destination_airport"],
            aircraft_id=flight["aircraft_id"],
            aircraft_type=flight["aircraft_type"],
            features=features,
        )
        history[row.route_id].append(row)
        rows.append(row)
    if not rows:
        raise DisruptionFeatureEngineeringError("No disruption feature rows could be built.")
    return rows


def _weather_features(
    events: list[dict[str, str]], origin: str, destination: str, departure: datetime
) -> dict[str, float | bool]:
    eligible = [
        row
        for row in events
        if row["airport_code"] in {origin, destination}
        and _parse_dt(row["event_start_utc"]) <= departure
        and _parse_dt(row["event_end_utc"]) >= departure
    ]
    return {
        "max_weather_impact_score": max(
            (_float(row["operational_impact_score"]) / 100.0 for row in eligible), default=0.0
        ),
        "origin_weather_event_count": sum(1 for row in eligible if row["airport_code"] == origin),
        "destination_weather_event_count": sum(1 for row in eligible if row["airport_code"] == destination),
        "severe_weather_flag": any(_float(row["severity"]) >= 4 for row in eligible),
        "weather_exposure_flag": bool(eligible),
    }


def _airport_features(
    events: list[dict[str, object]], origin: str, destination: str, departure: datetime
) -> dict[str, float | bool]:
    eligible = [
        row
        for row in events
        if str(row["airport_code"]) in {origin, destination}
        and _parse_dt(str(row["event_start_utc"])) <= departure
        and _parse_dt(str(row["event_end_utc"])) >= departure
    ]
    return {
        "airport_event_count": float(len(eligible)),
        "maximum_airport_event_severity": max((_float(row["severity"]) for row in eligible), default=0.0),
        "maximum_capacity_reduction_percent": max(
            (_float(row["capacity_reduction_percent"]) for row in eligible), default=0.0
        ),
        "estimated_airport_event_delay": max((_float(row["estimated_delay_minutes"]) for row in eligible), default=0.0),
        "airport_event_exposure_flag": bool(eligible),
    }


def _optional_forecast_features(row: dict[str, str] | None, flight: dict[str, str]) -> dict[str, float | bool]:
    if row is None:
        return {
            "optional_passenger_forecast_used": False,
            "forecast_passengers": 0.0,
            "forecast_load_factor": 0.0,
            "demand_uncertainty_width": 0.0,
            "forecast_constraint_applied": False,
        }
    return {
        "optional_passenger_forecast_used": True,
        "forecast_passengers": _float(row.get("forecast_passengers", 0.0)),
        "forecast_load_factor": _float(row.get("forecast_passengers", 0.0)) / max(1.0, _float(flight["seat_capacity"])),
        "demand_uncertainty_width": _float(row.get("forecast_upper_95", 0.0))
        - _float(row.get("forecast_lower_95", 0.0)),
        "forecast_constraint_applied": _truthy(str(row.get("constraint_applied", "False"))),
    }


def _optional_delay_features(row: dict[str, str] | None) -> dict[str, float | str | bool]:
    if row is None:
        return {
            "optional_delay_prediction_used": False,
            "predicted_delay_probability": 0.0,
            "predicted_delay_minutes": 0.0,
            "predicted_delay_risk_band": "",
            "predicted_weather_exposure_flag": False,
            "predicted_airport_event_exposure_flag": False,
        }
    return {
        "optional_delay_prediction_used": True,
        "predicted_delay_probability": _float(row.get("delay_probability", 0.0)),
        "predicted_delay_minutes": _float(row.get("estimated_delay_minutes", 0.0)),
        "predicted_delay_risk_band": row.get("risk_band", ""),
        "predicted_weather_exposure_flag": _truthy(str(row.get("weather_exposure_flag", "False"))),
        "predicted_airport_event_exposure_flag": _truthy(str(row.get("airport_event_exposure_flag", "False"))),
    }


def _optional_maintenance_features(row: dict[str, str] | None) -> dict[str, float | str | bool]:
    if row is None:
        return {
            "optional_maintenance_analytics_used": False,
            "maintenance_risk_score": 0.0,
            "aircraft_health_score": 1.0,
            "maintenance_alert_category": "",
        }
    return {
        "optional_maintenance_analytics_used": True,
        "maintenance_risk_score": _float(row.get("maintenance_risk_score", 0.0)),
        "aircraft_health_score": _float(row.get("aircraft_health_score", 1.0)),
        "maintenance_alert_category": row.get("alert_category", ""),
    }


def _context_flags(features: dict[str, float | str | bool]) -> dict[str, bool]:
    return {
        "weather_disruption_flag": bool(features["weather_exposure_flag"]),
        "airport_disruption_flag": bool(features["airport_event_exposure_flag"]),
        "aircraft_disruption_flag": _float(features["source_maintenance_risk_score"]) > 0.6
        or _float(features["maintenance_risk_score"]) > 0.6,
        "passenger_pressure_flag": _float(features["latest_booking_load_factor"]) > 0.9
        or _float(features["forecast_load_factor"]) > 0.9,
        "network_reactionary_flag": _float(features["reactionary_delay_minutes"]) > 0
        or _float(features["prior_route_delay_pressure"]) > 0.5,
    }


def _latest_demand(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["flight_id"]].append(row)
    return {
        flight_id: min(items, key=lambda row: (int(row["days_before_departure"]), row["observation_date"]))
        for flight_id, items in grouped.items()
    }


def _latest_health(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["flight_id"])].append(row)
    return {
        flight_id: max(items, key=lambda row: str(row["event_timestamp_utc"])) for flight_id, items in grouped.items()
    }


def _prior_delay_pressure(rows: list[DisruptionFeatureRow]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if _float(row.features["departure_delay_minutes"]) >= 15) / len(rows)


def _same_day_route_count(rows: list[DisruptionFeatureRow], operating_date: str) -> float:
    return float(
        sum(
            1
            for row in rows
            if row.operating_date == operating_date and _float(row.features["departure_delay_minutes"]) >= 15
        )
    )


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _truthy(value: str) -> bool:
    return value.lower() == "true"


def _float(value: object) -> float:
    if value in {"", None}:
        return 0.0
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
