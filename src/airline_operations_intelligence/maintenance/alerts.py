"""Maintenance alert generation."""

from __future__ import annotations

import hashlib

from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow, MaintenanceAlert, MaintenanceScore

SYNTHETIC_WARNING = "Synthetic data only; not certified maintenance evidence."


def generate_alerts(
    maintenance_run_id: str,
    rows: list[HealthFeatureRow],
    scores: list[MaintenanceScore],
    maximum_alerts_per_aircraft: int,
) -> list[MaintenanceAlert]:
    """Generate deterministic conservative maintenance alerts."""
    rows_by_id = {row.health_observation_id: row for row in rows}
    alert_candidates = [score for score in scores if score.alert_category != "none"]
    grouped: dict[str, list[MaintenanceScore]] = {}
    for score in alert_candidates:
        grouped.setdefault(score.aircraft_id, []).append(score)
    alerts: list[MaintenanceAlert] = []
    for _aircraft_id, aircraft_scores in sorted(grouped.items()):
        ordered = sorted(
            aircraft_scores,
            key=lambda score: (
                -score.maintenance_risk_score,
                score.event_timestamp_utc.isoformat(),
                score.telemetry_id,
            ),
        )[:maximum_alerts_per_aircraft]
        for score in ordered:
            row = rows_by_id[score.health_observation_id]
            alerts.append(
                MaintenanceAlert(
                    alert_id=_alert_id(maintenance_run_id, score),
                    aircraft_id=score.aircraft_id,
                    aircraft_type=score.aircraft_type,
                    telemetry_id=score.telemetry_id,
                    flight_id=score.flight_id,
                    event_timestamp_utc=score.event_timestamp_utc.isoformat(),
                    alert_category=score.alert_category,
                    risk_band=score.risk_band,
                    maintenance_risk_score=score.maintenance_risk_score,
                    aircraft_health_score=score.aircraft_health_score,
                    primary_reason=score.top_contributing_factor,
                    contributing_factors=score.contributing_factors,
                    recommended_review_action=_action(score.alert_category),
                    evidence_fields=_evidence(row, score),
                    synthetic_data_warning=SYNTHETIC_WARNING,
                    human_review_required=True,
                )
            )
    return sorted(alerts, key=lambda alert: (alert.aircraft_id, alert.event_timestamp_utc, alert.alert_id))


def _alert_id(maintenance_run_id: str, score: MaintenanceScore) -> str:
    payload = f"{maintenance_run_id}|{score.aircraft_id}|{score.telemetry_id}|{score.alert_category}"
    return f"MAINT-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12].upper()}"


def _action(category: str) -> str:
    if category == "action_recommended":
        return "Prioritise engineering review in a real system; do not treat as certified maintenance instruction."
    if category == "watch":
        return "Inspect source telemetry evidence and review synthetic trend."
    return "Review synthetic telemetry trend."


def _evidence(row: HealthFeatureRow, score: MaintenanceScore) -> dict[str, float | str | bool]:
    return {
        "engine_vibration_max": _num(row.features["engine_vibration_max"]),
        "engine_temperature_max": _num(row.features["engine_temperature_max"]),
        "brake_temperature_c": _num(row.features["brake_temperature_c"]),
        "fault_code": str(row.features["fault_code"]),
        "top_contributing_factor": score.top_contributing_factor,
    }


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
