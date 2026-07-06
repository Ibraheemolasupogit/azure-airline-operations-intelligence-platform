from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import DelayPredictionConfigurationError
from airline_operations_intelligence.delay_prediction.config import (
    build_delay_run_id,
    load_delay_prediction_config,
    parse_delay_prediction_config,
    with_overrides,
)


def test_delay_prediction_config_loads_ci_profile() -> None:
    config = load_delay_prediction_config("configs/delay_prediction_ci.yaml")

    assert config.settings.target == "departure_delay_15_flag"
    assert config.settings.delay_threshold_minutes == 75
    assert "logistic_regression" in config.settings.enabled_models


def test_delay_prediction_config_rejects_random_split() -> None:
    raw = _minimal_raw_config()
    raw["splitting"]["strategy"] = "random"

    with pytest.raises(DelayPredictionConfigurationError, match="chronological"):
        parse_delay_prediction_config(raw)


def test_delay_prediction_config_rejects_bad_model_root() -> None:
    raw = _minimal_raw_config()
    raw["delay_prediction"]["model_root"] = "models/delay_prediction"

    with pytest.raises(DelayPredictionConfigurationError, match="outputs/models/delay_prediction"):
        parse_delay_prediction_config(raw)


def test_delay_run_id_and_overrides_are_deterministic() -> None:
    config = load_delay_prediction_config("configs/delay_prediction_ci.yaml")
    updated = with_overrides(
        config,
        seed=99,
        output_root=Path("outputs/delay_prediction/test"),
        delay_threshold_minutes=30,
        overwrite=True,
    )

    assert updated.settings.seed == 99
    assert updated.settings.overwrite is True
    assert updated.settings.delay_threshold_minutes == 30
    assert build_delay_run_id(config, "validation-a", None, None) == build_delay_run_id(
        config,
        "validation-a",
        None,
        None,
    )
    assert build_delay_run_id(config, "validation-a", "forecast-a", "manual") == "manual"


def _minimal_raw_config() -> dict[str, object]:
    return {
        "delay_prediction": {
            "target": "departure_delay_15_flag",
            "delay_threshold_minutes": 15,
            "prediction_cutoff_minutes": 120,
            "output_root": "outputs/delay_prediction",
            "model_root": "outputs/models/delay_prediction",
            "report_root": "reports/delay_prediction",
            "overwrite": False,
            "seed": 1,
            "champion_selection_metric": "pr_auc",
            "champion_selection_direction": "maximize",
            "minimum_improvement_over_baseline": 0.0,
            "enable_secondary_delay_regression": True,
        },
        "data": {
            "required_validation_status": ["passed"],
            "exclude_cancelled_flights": True,
            "include_diverted_flights_with_valid_departure": True,
            "minimum_training_rows": 10,
            "minimum_positive_rows": 1,
            "minimum_negative_rows": 1,
            "allow_optional_passenger_forecast_input": True,
        },
        "splitting": {
            "strategy": "chronological",
            "train_fraction": 0.6,
            "validation_fraction": 0.2,
            "test_fraction": 0.2,
            "minimum_train_rows": 6,
            "minimum_validation_rows": 2,
            "minimum_test_rows": 2,
            "temporal_gap_days": 0,
        },
        "features": {
            "use_route": True,
            "use_origin_airport": True,
            "use_destination_airport": True,
            "use_aircraft_type": True,
            "use_seat_capacity": True,
            "use_scheduled_block_minutes": True,
            "use_departure_hour": True,
            "use_day_of_week": True,
            "use_month": True,
            "use_weekend_flag": True,
            "use_service_type": True,
            "use_schedule_status": True,
            "use_predeparture_weather": True,
            "use_predeparture_airport_events": True,
            "use_predeparture_crew_state": True,
            "use_predeparture_aircraft_health": True,
            "use_historical_route_delay_features": True,
            "use_historical_airport_delay_features": True,
            "use_historical_aircraft_delay_features": True,
            "use_optional_passenger_forecast": True,
            "historical_windows": [7],
        },
        "models": {
            "majority_class_baseline": {"enabled": True},
            "route_historical_rate_baseline": {"enabled": True},
            "logistic_regression": {"enabled": True},
        },
        "classification": {
            "default_probability_threshold": 0.5,
            "threshold_selection_metric": "f1",
            "threshold_search_values": [0.3, 0.5],
        },
        "evaluation": {
            "metrics": ["roc_auc", "pr_auc", "log_loss", "brier_score", "precision", "recall", "f1"],
            "evaluate_by_route": True,
            "evaluate_by_origin_airport": True,
            "evaluate_by_time_band": True,
            "evaluate_by_weather_exposure": True,
            "probability_bins": 5,
        },
        "risk_bands": {
            "low": {"minimum_probability": 0.0, "maximum_probability": 0.5},
            "high": {"minimum_probability": 0.5, "maximum_probability": 1.0},
        },
    }
