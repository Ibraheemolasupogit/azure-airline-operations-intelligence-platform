"""Writers for maintenance analytics artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow, MaintenanceAlert, MaintenanceScore


def write_json(path: Path, payload: object) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write deterministic JSONL and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    return sha256_file(path)


def write_rows_csv(path: Path, rows: list[dict[str, object]]) -> str:
    """Write CSV rows and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def write_features(path: Path, run_id: str, rows: list[HealthFeatureRow]) -> str:
    """Write health feature rows."""
    payload: list[dict[str, object]] = []
    for row in rows:
        payload.append(
            {
                "maintenance_run_id": run_id,
                "health_observation_id": row.health_observation_id,
                "aircraft_id": row.aircraft_id,
                "aircraft_type": row.aircraft_type,
                "telemetry_id": row.telemetry_id,
                "flight_id": row.flight_id,
                "event_timestamp_utc": row.event_timestamp_utc.isoformat(),
                "operating_date": row.operating_date,
                **row.features,
                **row.context,
            }
        )
    return write_rows_csv(path, payload)


def write_scores(path: Path, run_id: str, scores: list[MaintenanceScore]) -> str:
    """Write health score rows."""
    rows = [
        {
            "maintenance_run_id": run_id,
            "aircraft_id": score.aircraft_id,
            "aircraft_type": score.aircraft_type,
            "telemetry_id": score.telemetry_id,
            "flight_id": score.flight_id,
            "event_timestamp_utc": score.event_timestamp_utc.isoformat(),
            "sensor_threshold_score": score.component_scores["sensor_thresholds"],
            "telemetry_anomaly_score": score.component_scores["telemetry_anomaly"],
            "degradation_trend_score": score.component_scores["degradation_trend"],
            "fault_code_score": score.component_scores["fault_code"],
            "utilisation_score": score.component_scores["utilisation"],
            "operational_context_score": score.component_scores["recent_delay_or_operational_context"],
            "maintenance_risk_score": score.maintenance_risk_score,
            "aircraft_health_score": score.aircraft_health_score,
            "risk_band": score.risk_band,
            "alert_category": score.alert_category,
            "top_contributing_factor": score.top_contributing_factor,
            "human_review_required": score.human_review_required,
        }
        for score in scores
    ]
    return write_rows_csv(path, rows)


def alert_payloads(alerts: list[MaintenanceAlert]) -> list[dict[str, Any]]:
    """Return JSON-serialisable alerts."""
    return [
        {
            **alert.__dict__,
            "contributing_factors": list(alert.contributing_factors),
        }
        for alert in alerts
    ]
