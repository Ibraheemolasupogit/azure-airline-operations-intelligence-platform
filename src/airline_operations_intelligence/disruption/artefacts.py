"""Writers for disruption scoring artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.disruption.contracts import DisruptionAlert, DisruptionFeatureRow, DisruptionScore


def write_json(path: Path, payload: object) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write deterministic JSONL rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    return sha256_file(path)


def write_rows_csv(path: Path, rows: list[dict[str, object]]) -> str:
    """Write CSV rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def write_features(path: Path, run_id: str, rows: list[DisruptionFeatureRow]) -> str:
    """Write disruption features."""
    payload: list[dict[str, object]] = [
        {
            "disruption_run_id": run_id,
            "flight_id": row.flight_id,
            "route_id": row.route_id,
            "operating_date": row.operating_date,
            "scheduled_departure_utc": row.scheduled_departure_utc,
            "origin_airport": row.origin_airport,
            "destination_airport": row.destination_airport,
            "aircraft_id": row.aircraft_id,
            "aircraft_type": row.aircraft_type,
            **row.features,
        }
        for row in rows
    ]
    return write_rows_csv(path, payload)


def write_scores(path: Path, run_id: str, scores: list[DisruptionScore]) -> str:
    """Write disruption scores."""
    rows = [
        {
            "disruption_run_id": run_id,
            "flight_id": score.flight_id,
            "route_id": score.route_id,
            "operating_date": score.operating_date,
            "scheduled_departure_utc": score.scheduled_departure_utc,
            "origin_airport": score.origin_airport,
            "destination_airport": score.destination_airport,
            "aircraft_id": score.aircraft_id,
            "delay_component_score": score.component_scores["delay"],
            "weather_component_score": score.component_scores["weather"],
            "airport_event_component_score": score.component_scores["airport_events"],
            "crew_component_score": score.component_scores["crew"],
            "aircraft_health_component_score": score.component_scores["aircraft_health"],
            "passenger_pressure_component_score": score.component_scores["passenger_pressure"],
            "network_reactionary_component_score": score.component_scores["network_reactionary"],
            "forward_disruption_risk_score": score.forward_disruption_risk_score,
            "retrospective_disruption_score": score.retrospective_disruption_score,
            "disruption_severity_score": score.disruption_severity_score,
            "disruption_risk_band": score.disruption_risk_band,
            "recovery_priority": score.recovery_priority,
            "primary_disruption_driver": score.primary_disruption_driver,
            "contributing_factors": "|".join(score.contributing_factors),
            "recommended_review_action": score.recommended_review_action,
            "human_review_required": score.human_review_required,
            "optional_passenger_forecast_used": score.optional_passenger_forecast_used,
            "optional_delay_prediction_used": score.optional_delay_prediction_used,
            "optional_maintenance_analytics_used": score.optional_maintenance_analytics_used,
        }
        for score in scores
    ]
    return write_rows_csv(path, rows)


def alert_payloads(alerts: list[DisruptionAlert]) -> list[dict[str, Any]]:
    """Return JSON-serialisable alerts."""
    return [{**alert.__dict__, "contributing_factors": list(alert.contributing_factors)} for alert in alerts]
