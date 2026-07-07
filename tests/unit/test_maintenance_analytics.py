from datetime import UTC, datetime

from airline_operations_intelligence.maintenance.alerts import generate_alerts
from airline_operations_intelligence.maintenance.config import load_maintenance_config
from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow
from airline_operations_intelligence.maintenance.evaluation import aircraft_summary, flight_risk, maintenance_metrics
from airline_operations_intelligence.maintenance.features import _sensor_flags
from airline_operations_intelligence.maintenance.scoring import alert_category_for, risk_band_for, score_health_rows


def test_sensor_flags_and_scoring_are_bounded() -> None:
    config = load_maintenance_config("configs/maintenance_analytics_ci.yaml")
    row = _row("OBS-1", vibration=7.0, fault_code="SYN-FLT")

    flags = _sensor_flags(row.features, config.settings.telemetry_bounds)
    scores = score_health_rows([row], config)

    assert flags["vibration_warning_flag"] is True
    assert 0 <= scores[0].maintenance_risk_score <= 1
    assert 0 <= scores[0].aircraft_health_score <= 1
    assert scores[0].top_contributing_factor


def test_risk_band_alert_category_and_alert_id_are_deterministic() -> None:
    config = load_maintenance_config("configs/maintenance_analytics_ci.yaml")
    rows = [_row("OBS-1", vibration=7.2, fault_code="SYN-FLT")]
    scores = score_health_rows(rows, config)
    alerts_a = generate_alerts("run-a", rows, scores, 5)
    alerts_b = generate_alerts("run-a", rows, scores, 5)

    assert risk_band_for(0.19, config) == "medium"
    assert alert_category_for(0.19, config) == "watch"
    assert alerts_a == alerts_b
    assert alerts_a[0].human_review_required is True
    assert "certified" in alerts_a[0].recommended_review_action or "Inspect" in alerts_a[0].recommended_review_action


def test_summaries_metrics_and_flight_risk_reconcile() -> None:
    config = load_maintenance_config("configs/maintenance_analytics_ci.yaml")
    rows = [_row("OBS-1", vibration=7.2, fault_code="SYN-FLT"), _row("OBS-2", vibration=2.0, fault_code="")]
    scores = score_health_rows(rows, config)
    alerts = generate_alerts("run-a", rows, scores, 5)

    assert len(aircraft_summary("run-a", scores)) == 1
    assert len(flight_risk("run-a", rows, scores)) == 2
    metrics = maintenance_metrics("run-a", rows, scores, alerts)
    assert {row["metric_name"] for row in metrics} >= {"telemetry_observation_count", "scored_observation_count"}


def _row(observation_id: str, vibration: float, fault_code: str) -> HealthFeatureRow:
    features = {
        "engine_1_vibration": vibration,
        "engine_2_vibration": vibration - 0.2,
        "engine_vibration_max": vibration,
        "engine_vibration_delta": 0.2,
        "engine_1_temperature_c": 700.0,
        "engine_2_temperature_c": 710.0,
        "engine_temperature_max": 710.0,
        "engine_temperature_delta": 10.0,
        "hydraulic_pressure_psi": 3000.0,
        "oil_pressure_psi": 60.0,
        "fuel_flow_kg_h": 1800.0,
        "brake_temperature_c": 200.0,
        "cycles_since_maintenance": 250.0,
        "flight_hours_since_maintenance": 700.0,
        "source_maintenance_risk_score": 0.5,
        "health_status": "normal",
        "fault_code": fault_code,
        "fault_code_present": bool(fault_code),
        "vibration_warning_flag": vibration > 6.0,
        "vibration_critical_flag": vibration > 8.0,
        "engine_temperature_warning_flag": False,
        "engine_temperature_critical_flag": False,
        "hydraulic_pressure_warning_flag": False,
        "hydraulic_pressure_critical_flag": False,
        "oil_pressure_warning_flag": False,
        "oil_pressure_critical_flag": False,
        "brake_temperature_warning_flag": False,
        "brake_temperature_critical_flag": False,
        "degradation_trend_score": 0.2,
        "rolling_fault_code_count": 1.0 if fault_code else 0.0,
        "utilisation_intensity": 0.7,
        "recent_aircraft_delay_rate": 0.2,
    }
    return HealthFeatureRow(
        health_observation_id=observation_id,
        aircraft_id="SYN-A320-001",
        aircraft_type="A320",
        telemetry_id=observation_id,
        flight_id=f"FLT-{observation_id}",
        event_timestamp_utc=datetime(2025, 1, 1, tzinfo=UTC),
        operating_date="2025-01-01",
        features=features,
        context={"retrospective_departure_delay_minutes": 20.0},
    )
