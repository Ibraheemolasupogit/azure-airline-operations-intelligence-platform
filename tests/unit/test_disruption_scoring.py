from airline_operations_intelligence.common.exceptions import DisruptionLeakageDetectedError
from airline_operations_intelligence.disruption.alerts import generate_disruption_alerts
from airline_operations_intelligence.disruption.config import load_disruption_config
from airline_operations_intelligence.disruption.contracts import DisruptionFeatureRow
from airline_operations_intelligence.disruption.leakage import assert_forward_risk_inputs
from airline_operations_intelligence.disruption.scoring import score_disruption_rows
from airline_operations_intelligence.disruption.summaries import daily_summary, disruption_metrics, route_summary


def test_disruption_scoring_components_and_alerts_are_deterministic() -> None:
    config = load_disruption_config("configs/disruption_scoring_ci.yaml")
    rows = [_row("FLT-1", delay=75.0), _row("FLT-2", delay=5.0)]
    scores, checks = score_disruption_rows(rows, config)
    alerts_a = generate_disruption_alerts("run-a", rows, scores, 10)
    alerts_b = generate_disruption_alerts("run-a", rows, scores, 10)

    assert checks
    assert all(0 <= score.disruption_severity_score <= 1 for score in scores)
    assert scores[0].primary_disruption_driver
    assert alerts_a == alerts_b
    assert alerts_a[0].human_review_required is True


def test_forward_leakage_detection() -> None:
    try:
        assert_forward_risk_inputs({"departure_delay_minutes"})
    except DisruptionLeakageDetectedError as exc:
        assert "departure_delay_minutes" in str(exc)
    else:
        raise AssertionError("DisruptionLeakageDetectedError was not raised")


def test_disruption_summaries_and_metrics_reconcile() -> None:
    config = load_disruption_config("configs/disruption_scoring_ci.yaml")
    rows = [_row("FLT-1", delay=75.0), _row("FLT-2", delay=5.0)]
    scores, _ = score_disruption_rows(rows, config)
    alerts = generate_disruption_alerts("run-a", rows, scores, 10)

    assert len(route_summary("run-a", scores, rows)) == 1
    assert len(daily_summary("run-a", scores, alerts)) == 1
    assert {row["metric_name"] for row in disruption_metrics("run-a", scores, alerts)} >= {
        "flight_count",
        "alert_count",
    }


def _row(flight_id: str, delay: float) -> DisruptionFeatureRow:
    features = {
        "seat_capacity": 180.0,
        "departure_delay_minutes": delay,
        "arrival_delay_minutes": delay,
        "cancelled_flag": False,
        "diverted_flag": False,
        "reactionary_delay_minutes": 20.0,
        "predicted_delay_probability": 0.4,
        "predicted_delay_minutes": 30.0,
        "prior_route_delay_pressure": 0.5,
        "same_day_route_disruption_count": 1.0,
        "max_weather_impact_score": 0.5,
        "severe_weather_flag": False,
        "maximum_capacity_reduction_percent": 10.0,
        "estimated_airport_event_delay": 10.0,
        "maximum_airport_event_severity": 2.0,
        "captain_available": True,
        "first_officer_available": True,
        "crew_shortage_flag": False,
        "reserve_crew_used": True,
        "connection_risk_minutes": 50.0,
        "crew_disruption_flag": True,
        "source_maintenance_risk_score": 0.2,
        "maintenance_risk_score": 0.3,
        "aircraft_health_score": 0.8,
        "optional_maintenance_analytics_used": True,
        "latest_booking_load_factor": 0.9,
        "forecast_load_factor": 0.0,
        "demand_uncertainty_width": 0.0,
        "optional_passenger_forecast_used": False,
        "optional_delay_prediction_used": False,
    }
    return DisruptionFeatureRow(
        flight_id=flight_id,
        route_id="LHR-AMS",
        operating_date="2025-01-01",
        scheduled_departure_utc="2025-01-01T08:00:00Z",
        origin_airport="LHR",
        destination_airport="AMS",
        aircraft_id="SYN-A320-001",
        aircraft_type="A320",
        features=features,
    )
