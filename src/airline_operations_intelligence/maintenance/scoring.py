"""Maintenance-risk scoring."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import MaintenanceScoringError
from airline_operations_intelligence.maintenance.anomalies import anomaly_scores
from airline_operations_intelligence.maintenance.config import MaintenanceAnalyticsConfig
from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow, MaintenanceScore

COMPONENT_LABELS = {
    "sensor_thresholds": "sensor threshold breach",
    "telemetry_anomaly": "telemetry anomaly",
    "degradation_trend": "degradation trend",
    "fault_code": "fault-code evidence",
    "utilisation": "utilisation since maintenance",
    "recent_delay_or_operational_context": "retrospective operational context",
}


def score_health_rows(rows: list[HealthFeatureRow], config: MaintenanceAnalyticsConfig) -> list[MaintenanceScore]:
    """Calculate deterministic maintenance scores."""
    if not rows:
        raise MaintenanceScoringError("Maintenance scoring requires feature rows.")
    anomaly_by_id = anomaly_scores(rows) if config.settings.enable_statistical_anomaly_detection else {}
    scores: list[MaintenanceScore] = []
    for row in rows:
        components = {
            "sensor_thresholds": _sensor_score(row),
            "telemetry_anomaly": anomaly_by_id.get(row.health_observation_id, 0.0),
            "degradation_trend": _bounded(_num(row.features["degradation_trend_score"])),
            "fault_code": _fault_score(row),
            "utilisation": _bounded(_num(row.features["utilisation_intensity"])),
            "recent_delay_or_operational_context": _bounded(_num(row.features["recent_aircraft_delay_rate"])),
        }
        risk = round(
            sum(components[name] * config.settings.risk_weights[name] for name in config.settings.risk_weights), 6
        )
        health = round(1.0 - risk, 6)
        contributing = tuple(
            COMPONENT_LABELS[name]
            for name, value in sorted(components.items(), key=lambda item: (-item[1], item[0]))
            if value > 0
        )
        risk_band = risk_band_for(risk, config)
        alert_category = alert_category_for(risk, config)
        scores.append(
            MaintenanceScore(
                health_observation_id=row.health_observation_id,
                aircraft_id=row.aircraft_id,
                aircraft_type=row.aircraft_type,
                telemetry_id=row.telemetry_id,
                flight_id=row.flight_id,
                event_timestamp_utc=row.event_timestamp_utc,
                component_scores=components,
                maintenance_risk_score=risk,
                aircraft_health_score=health,
                risk_band=risk_band,
                alert_category=alert_category,
                top_contributing_factor=contributing[0] if contributing else "no elevated component",
                contributing_factors=contributing,
                human_review_required=alert_category != "none",
            )
        )
    return scores


def risk_band_for(score: float, config: MaintenanceAnalyticsConfig) -> str:
    """Assign risk band."""
    thresholds = config.settings.risk_score_thresholds
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["medium"]:
        return "medium"
    return "low"


def alert_category_for(score: float, config: MaintenanceAnalyticsConfig) -> str:
    """Assign alert category."""
    thresholds = config.settings.alert_thresholds
    if score >= thresholds["action_recommended"]:
        return "action_recommended"
    if score >= thresholds["watch"]:
        return "watch"
    if score >= thresholds["advisory"]:
        return "advisory"
    return "none"


def _sensor_score(row: HealthFeatureRow) -> float:
    critical = sum(1 for name, value in row.features.items() if name.endswith("_critical_flag") and bool(value))
    warning = sum(1 for name, value in row.features.items() if name.endswith("_warning_flag") and bool(value))
    return _bounded(critical * 0.35 + warning * 0.15)


def _fault_score(row: HealthFeatureRow) -> float:
    present = 0.7 if bool(row.features["fault_code_present"]) else 0.0
    repeats = min(0.3, _num(row.features["rolling_fault_code_count"]) * 0.1)
    return _bounded(present + repeats)


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
