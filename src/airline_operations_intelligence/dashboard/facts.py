"""Fact table builders for dashboard outputs."""

from __future__ import annotations

from typing import Any


def build_facts(
    run_id: str, tables: dict[str, list[dict[str, Any]]], source_run_ids: dict[str, str | None]
) -> dict[str, list[dict[str, object]]]:
    """Build star-schema-friendly fact tables."""
    delays = {row["flight_id"]: row for row in tables["delay_history"]}
    flights = []
    for row in tables["flight_schedule"]:
        delay = delays.get(row["flight_id"], {})
        flights.append(
            {
                "dashboard_run_id": run_id,
                "flight_id": row["flight_id"],
                "flight_number": row["flight_number"],
                "operating_date": row["operating_date"],
                "scheduled_departure_utc": row["scheduled_departure_utc"],
                "origin_airport": row["origin_airport"],
                "destination_airport": row["destination_airport"],
                "route_id": row["route_id"],
                "aircraft_id": row["aircraft_id"],
                "aircraft_type": row["aircraft_type"],
                "seat_capacity": _int(row.get("seat_capacity")),
                "departure_delay_minutes": _float(delay.get("departure_delay_minutes")),
                "arrival_delay_minutes": _float(delay.get("arrival_delay_minutes")),
                "cancelled_flag": _bool(delay.get("cancelled_flag")),
                "diverted_flag": _bool(delay.get("diverted_flag")),
                "primary_delay_cause": delay.get("primary_delay_cause", ""),
                "reactionary_delay_minutes": _float(delay.get("reactionary_delay_minutes")),
                "source_domain": "validation",
                "source_run_id": source_run_ids.get("validation", ""),
            }
        )
    return {
        "fact_flight_operations": flights,
        "fact_passenger_demand": [
            {
                "dashboard_run_id": run_id,
                "flight_id": row["flight_id"],
                "observation_date": row["observation_date"],
                "operating_date": _flight_date(row["flight_id"]),
                "route_id": row["route_id"],
                "days_before_departure": _int(row.get("days_before_departure")),
                "booked_passengers": _int(row.get("booked_passengers")),
                "expected_final_passengers": _int(row.get("expected_final_passengers")),
                "seat_capacity": _int(row.get("seat_capacity")),
                "load_factor": _float(row.get("load_factor")),
                "booking_velocity": _float(row.get("booking_velocity")),
                "source_domain": "validation",
                "source_run_id": source_run_ids.get("validation", ""),
            }
            for row in tables["passenger_demand"]
        ],
        "fact_passenger_forecast": [
            {
                "dashboard_run_id": run_id,
                "flight_id": row.get("flight_id", ""),
                "route_id": row.get("route_id", ""),
                "operating_date": row.get("operating_date", ""),
                "forecast_passengers": _int(row.get("forecast_passengers")),
                "forecast_lower_80": _int(row.get("forecast_lower_80")),
                "forecast_upper_80": _int(row.get("forecast_upper_80")),
                "actual_passengers": _float(row.get("actual_passengers")),
                "forecast_load_factor": _safe_div(
                    _float(row.get("forecast_passengers")), _float(row.get("seat_capacity"))
                ),
                "absolute_error": _float(row.get("absolute_error")),
                "partition": row.get("partition", ""),
                "source_domain": "passenger_forecasting",
                "source_run_id": source_run_ids.get("passenger_forecasting", ""),
            }
            for row in tables.get("passenger_forecast", [])
        ],
        "fact_delay_prediction": [
            {
                "dashboard_run_id": run_id,
                "flight_id": row.get("flight_id", ""),
                "route_id": row.get("route_id", ""),
                "operating_date": row.get("operating_date", ""),
                "delay_probability": _float(row.get("delay_probability")),
                "predicted_delay_flag": _bool(row.get("predicted_delay_flag")),
                "risk_band": row.get("risk_band", ""),
                "estimated_delay_minutes": _float(row.get("estimated_delay_minutes")),
                "actual_delay_flag": _bool(row.get("actual_delay_flag")),
                "actual_delay_minutes": _float(row.get("actual_delay_minutes")),
                "partition": row.get("partition", ""),
                "source_domain": "delay_prediction",
                "source_run_id": source_run_ids.get("delay_prediction", ""),
            }
            for row in tables.get("delay_predictions", [])
        ],
        "fact_maintenance_risk": [
            {
                "dashboard_run_id": run_id,
                "flight_id": row.get("flight_id", ""),
                "aircraft_id": row.get("aircraft_id", ""),
                "aircraft_type": row.get("aircraft_type", ""),
                "maintenance_risk_score": _float(row.get("maintenance_risk_score")),
                "aircraft_health_score": _float(row.get("aircraft_health_score")),
                "risk_band": row.get("risk_band", ""),
                "alert_category": row.get("alert_category", ""),
                "human_review_required": _bool(row.get("human_review_required")),
                "source_domain": "maintenance_analytics",
                "source_run_id": source_run_ids.get("maintenance_analytics", ""),
            }
            for row in tables.get("maintenance_risk", [])
        ],
        "fact_disruption_score": [
            {
                "dashboard_run_id": run_id,
                "flight_id": row.get("flight_id", ""),
                "route_id": row.get("route_id", ""),
                "operating_date": row.get("operating_date", ""),
                "disruption_severity_score": _float(row.get("disruption_severity_score")),
                "forward_disruption_risk_score": _float(row.get("forward_disruption_risk_score")),
                "retrospective_disruption_score": _float(row.get("retrospective_disruption_score")),
                "disruption_risk_band": row.get("disruption_risk_band", ""),
                "recovery_priority": row.get("recovery_priority", ""),
                "primary_disruption_driver": row.get("primary_disruption_driver", ""),
                "weather_component_score": _float(row.get("weather_component_score")),
                "delay_component_score": _float(row.get("delay_component_score")),
                "crew_component_score": _float(row.get("crew_component_score")),
                "aircraft_health_component_score": _float(row.get("aircraft_health_component_score")),
                "human_review_required": _bool(row.get("human_review_required")),
                "source_domain": "disruption_scoring",
                "source_run_id": source_run_ids.get("disruption_scoring", ""),
            }
            for row in tables.get("disruption_scores", [])
        ],
        "fact_monitoring_metric": [
            {
                "dashboard_run_id": run_id,
                "monitoring_domain": row.get("monitoring_domain", ""),
                "metric_name": row.get("metric_name", ""),
                "metric_value": _float(row.get("metric_value")),
                "status": row.get("status", ""),
                "severity": row.get("severity", ""),
                "threshold": row.get("threshold", ""),
                "evidence_path": row.get("evidence_path", ""),
                "source_domain": "monitoring",
                "source_run_id": row.get("source_run_id", source_run_ids.get("monitoring", "")),
            }
            for row in tables.get("monitoring_metrics", [])
        ],
        "fact_monitoring_alert": [
            {
                "dashboard_run_id": run_id,
                "monitoring_alert_id": row.get("monitoring_alert_id", row.get("alert_id", "")),
                "monitoring_domain": row.get("monitoring_domain", ""),
                "severity": row.get("severity", ""),
                "status": row.get("status", ""),
                "message": row.get("message", ""),
                "source_domain": "monitoring",
                "source_run_id": source_run_ids.get("monitoring", ""),
            }
            for row in tables.get("monitoring_alerts", [])
        ],
        "fact_assistant_response": [
            {
                "dashboard_run_id": run_id,
                **row,
                "source_domain": "genai_assistant",
                "source_run_id": source_run_ids.get("genai_assistant", ""),
            }
            for row in tables.get("assistant_response", [])
        ],
    }


def _int(value: object) -> int:
    return int(float(str(value or 0)))


def _float(value: object) -> float:
    return round(float(str(value or 0)), 6)


def _bool(value: object) -> bool:
    return str(value).lower() in {"true", "1", "yes"}


def _safe_div(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _flight_date(flight_id: str) -> str:
    parts = str(flight_id).split("-")
    if len(parts) >= 3 and len(parts[1]) == 8:
        return f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:]}"
    return ""
