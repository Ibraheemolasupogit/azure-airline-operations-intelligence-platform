from datetime import date

from airline_operations_intelligence.common.exceptions import LeakageDetectedError
from airline_operations_intelligence.forecasting.config import load_forecasting_config
from airline_operations_intelligence.forecasting.contracts import ModelRow, PartitionedRows
from airline_operations_intelligence.forecasting.evaluation import evaluate_predictions
from airline_operations_intelligence.forecasting.leakage import (
    assert_no_flight_crosses_partitions,
    assert_no_forbidden_features,
)
from airline_operations_intelligence.forecasting.models import apply_capacity_constraints, predict, train_model
from airline_operations_intelligence.forecasting.prediction_intervals import interval_bounds, residual_quantiles
from airline_operations_intelligence.forecasting.selection import select_champion
from airline_operations_intelligence.forecasting.splitting import chronological_split


def test_chronological_split_and_no_flight_leakage() -> None:
    config = load_forecasting_config("configs/passenger_forecasting_ci.yaml")
    rows = [_row(index) for index in range(10)]

    partitions = chronological_split(rows, config)

    assert partitions.train[0].operating_date < partitions.validation[0].operating_date
    assert partitions.validation[0].operating_date < partitions.test[0].operating_date
    assert assert_no_flight_crosses_partitions(partitions)


def test_forbidden_feature_detection() -> None:
    row = _row(1)
    row = ModelRow(**{**row.__dict__, "features": {"expected_final_passengers": 10.0}})

    try:
        assert_no_forbidden_features([row])
    except LeakageDetectedError as exc:
        assert "expected_final_passengers" in str(exc)
    else:
        raise AssertionError("LeakageDetectedError was not raised")


def test_baseline_and_linear_predictions_are_deterministic_and_constrained() -> None:
    config = load_forecasting_config("configs/passenger_forecasting_ci.yaml")
    rows = [_row(index) for index in range(8)]
    model = train_model("linear_regression", rows[:5], config)

    first = apply_capacity_constraints(predict(model, rows[5:]), rows[5:], True)
    second = apply_capacity_constraints(predict(model, rows[5:]), rows[5:], True)

    assert first == second
    assert all(pred.constrained_prediction >= 0 for pred in first)


def test_metrics_intervals_and_champion_selection() -> None:
    config = load_forecasting_config("configs/passenger_forecasting_ci.yaml")
    rows = [_row(index) for index in range(5)]
    baseline = train_model("historical_mean", rows[:3], config)
    predictions = apply_capacity_constraints(predict(baseline, rows[3:]), rows[3:], True)
    metrics = evaluate_predictions(rows[3:], predictions)
    quantiles = residual_quantiles(rows[3:], predictions, (0.8, 0.95))
    bounds = interval_bounds(predictions[0].constrained_prediction, quantiles)
    champion, rationale = select_champion(
        {"historical_mean": metrics, "seasonal_naive": {**metrics, "wape": metrics["wape"] + 0.1}},
        {"historical_mean": "baseline", "seasonal_naive": "baseline"},
        config,
    )

    assert set(metrics) >= {"mae", "rmse", "wape", "smape", "bias"}
    assert bounds["lower_80"] <= predictions[0].constrained_prediction <= bounds["upper_80"]
    assert champion == "historical_mean"
    assert "Selected" in rationale


def test_partition_crossing_detection() -> None:
    row = _row(1)
    partitions = PartitionedRows(train=[row], validation=[row], test=[_row(2)], boundaries={})

    try:
        assert_no_flight_crosses_partitions(partitions)
    except LeakageDetectedError as exc:
        assert row.flight_id in str(exc)
    else:
        raise AssertionError("LeakageDetectedError was not raised")


def _row(index: int) -> ModelRow:
    operating_date = date(2025, 1, 1).replace(day=1 + index)
    return ModelRow(
        observation_id=f"OBS-{index}",
        flight_id=f"FLT-{index}",
        route_id="LHR-AMS" if index % 2 == 0 else "AMS-LHR",
        operating_date=operating_date,
        observation_date=operating_date,
        days_before_departure=14,
        target=100.0 + index,
        seat_capacity=180,
        booked_passengers=80 + index,
        booking_velocity=1.2,
        cancellations_to_date=1,
        group_booking_count=0,
        demand_segment="balanced",
        discount_mix=0.5,
        standard_mix=0.35,
        flex_mix=0.15,
        day_of_week=operating_date.weekday(),
        month=operating_date.month,
        weekend_flag=0,
        historical_route_mean=100.0,
        historical_route_load_factor=0.7,
        historical_route_observations=index,
        features={
            "route_id": "LHR-AMS" if index % 2 == 0 else "AMS-LHR",
            "booked_passengers": float(80 + index),
            "seat_capacity": 180.0,
        },
        feature_availability={"booked_passengers": "available at booking-observation time"},
    )
