from datetime import UTC, date, datetime, timedelta

from airline_operations_intelligence.common.exceptions import DelayLeakageDetectedError
from airline_operations_intelligence.delay_prediction.config import load_delay_prediction_config
from airline_operations_intelligence.delay_prediction.contracts import DelayModelRow, PartitionedDelayRows
from airline_operations_intelligence.delay_prediction.evaluation import evaluate_probabilities
from airline_operations_intelligence.delay_prediction.leakage import (
    assert_no_flight_crosses_partitions,
    assert_no_forbidden_features,
)
from airline_operations_intelligence.delay_prediction.models import predict_probability, train_model
from airline_operations_intelligence.delay_prediction.selection import select_champion, select_threshold
from airline_operations_intelligence.delay_prediction.splitting import chronological_split


def test_chronological_split_and_no_flight_leakage() -> None:
    config = load_delay_prediction_config("configs/delay_prediction_ci.yaml")
    rows = [_row(index) for index in range(12)]

    partitions = chronological_split(rows, config)

    assert partitions.train[0].scheduled_departure_utc < partitions.validation[0].scheduled_departure_utc
    assert partitions.validation[0].scheduled_departure_utc < partitions.test[0].scheduled_departure_utc
    assert assert_no_flight_crosses_partitions(partitions)


def test_forbidden_delay_feature_detection() -> None:
    row = _row(1)
    row = DelayModelRow(**{**row.__dict__, "features": {"actual_departure_utc": 1.0}})

    try:
        assert_no_forbidden_features([row])
    except DelayLeakageDetectedError as exc:
        assert "actual_departure_utc" in str(exc)
    else:
        raise AssertionError("DelayLeakageDetectedError was not raised")


def test_delay_models_are_deterministic_probabilities() -> None:
    config = load_delay_prediction_config("configs/delay_prediction_ci.yaml")
    rows = [_row(index) for index in range(12)]
    model = train_model("logistic_regression", rows[:8], config)

    first = predict_probability(model, rows[8:])
    second = predict_probability(model, rows[8:])

    assert first == second
    assert all(0 <= probability <= 1 for probability in first)


def test_metrics_champion_and_threshold_selection() -> None:
    config = load_delay_prediction_config("configs/delay_prediction_ci.yaml")
    rows = [_row(index) for index in range(8)]
    probabilities = [0.2, 0.7, 0.4, 0.8]
    metrics = evaluate_probabilities(rows[:4], probabilities, 0.5)
    champion, rationale = select_champion(
        {
            "majority_class_baseline": metrics,
            "logistic_regression": {**metrics, "pr_auc": metrics["pr_auc"] + 0.1},
        },
        {"majority_class_baseline": "baseline", "logistic_regression": "candidate"},
        config,
    )
    threshold, threshold_rationale = select_threshold(
        [
            {"threshold": 0.3, "f1": 0.5, "recall": 1.0, "precision": 0.4},
            {"threshold": 0.5, "f1": 0.7, "recall": 0.8, "precision": 0.7},
        ],
        config,
    )

    assert set(metrics) >= {"roc_auc", "pr_auc", "log_loss", "brier_score", "f1"}
    assert champion == "logistic_regression"
    assert "Selected" in rationale
    assert threshold == 0.5
    assert "Selected" in threshold_rationale


def test_partition_crossing_detection() -> None:
    row = _row(1)
    partitions = PartitionedDelayRows(train=[row], validation=[row], test=[_row(2)], boundaries={})

    try:
        assert_no_flight_crosses_partitions(partitions)
    except DelayLeakageDetectedError as exc:
        assert row.flight_id in str(exc)
    else:
        raise AssertionError("DelayLeakageDetectedError was not raised")


def _row(index: int) -> DelayModelRow:
    scheduled = datetime(2025, 1, 1, 8, tzinfo=UTC) + timedelta(days=index)
    operating_date = date(2025, 1, 1).replace(day=1 + index)
    return DelayModelRow(
        observation_id=f"FLT-{index}",
        flight_id=f"FLT-{index}",
        route_id="LHR-AMS" if index % 2 == 0 else "AMS-LHR",
        origin_airport="LHR" if index % 2 == 0 else "AMS",
        destination_airport="AMS" if index % 2 == 0 else "LHR",
        aircraft_id=f"AC-{index % 3}",
        aircraft_type="A320",
        operating_date=operating_date,
        scheduled_departure_utc=scheduled,
        prediction_cutoff_utc=scheduled - timedelta(minutes=120),
        target=index % 2,
        delay_minutes=float(20 + index),
        seat_capacity=180,
        departure_hour=scheduled.hour,
        day_of_week=operating_date.weekday(),
        month=operating_date.month,
        weather_exposure_flag=index % 2,
        airport_event_exposure_flag=0,
        features={
            "route_id": "LHR-AMS" if index % 2 == 0 else "AMS-LHR",
            "seat_capacity": 180.0,
            "historical_route_delay_rate": 0.5,
            "departure_hour": float(scheduled.hour),
        },
        feature_availability={"route_id": "available at schedule creation"},
    )
