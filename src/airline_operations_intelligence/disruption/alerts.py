"""Disruption alert generation."""

from __future__ import annotations

import hashlib

from airline_operations_intelligence.disruption.contracts import DisruptionAlert, DisruptionFeatureRow, DisruptionScore

SYNTHETIC_WARNING = "Synthetic decision-support evidence only; not real disruption-management tooling."


def generate_disruption_alerts(
    disruption_run_id: str,
    feature_rows: list[DisruptionFeatureRow],
    scores: list[DisruptionScore],
    maximum_alerts: int,
) -> list[DisruptionAlert]:
    """Generate deterministic high-priority disruption alerts."""
    features_by_flight = {row.flight_id: row for row in feature_rows}
    candidates = [score for score in scores if score.human_review_required]
    ordered = sorted(
        candidates,
        key=lambda score: (-score.disruption_severity_score, score.scheduled_departure_utc, score.flight_id),
    )[:maximum_alerts]
    alerts: list[DisruptionAlert] = []
    for score in ordered:
        row = features_by_flight[score.flight_id]
        alerts.append(
            DisruptionAlert(
                alert_id=_alert_id(disruption_run_id, score),
                flight_id=score.flight_id,
                route_id=score.route_id,
                operating_date=score.operating_date,
                origin_airport=score.origin_airport,
                destination_airport=score.destination_airport,
                disruption_severity_score=score.disruption_severity_score,
                disruption_risk_band=score.disruption_risk_band,
                recovery_priority=score.recovery_priority,
                primary_disruption_driver=score.primary_disruption_driver,
                contributing_factors=score.contributing_factors,
                recommended_review_action=score.recommended_review_action,
                human_review_required=True,
                evidence_fields={
                    "departure_delay_minutes": _num(row.features["departure_delay_minutes"]),
                    "max_weather_impact_score": _num(row.features["max_weather_impact_score"]),
                    "connection_risk_minutes": _num(row.features["connection_risk_minutes"]),
                    "maintenance_risk_score": _num(row.features["maintenance_risk_score"]),
                },
                synthetic_data_warning=SYNTHETIC_WARNING,
            )
        )
    return sorted(alerts, key=lambda alert: (alert.operating_date, alert.flight_id, alert.alert_id))


def _alert_id(disruption_run_id: str, score: DisruptionScore) -> str:
    payload = f"{disruption_run_id}|{score.flight_id}|{score.disruption_risk_band}|{score.recovery_priority}"
    return f"DISR-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12].upper()}"


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
