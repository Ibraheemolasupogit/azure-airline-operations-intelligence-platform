from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import ForecastingConfigurationError
from airline_operations_intelligence.forecasting.config import (
    build_forecast_run_id,
    load_forecasting_config,
    parse_forecasting_config,
    with_overrides,
)


def test_forecasting_config_loads_ci_profile() -> None:
    config = load_forecasting_config("configs/passenger_forecasting_ci.yaml")

    assert config.settings.target == "expected_final_passengers"
    assert config.settings.prediction_horizon_days == 14
    assert "historical_mean" in config.settings.enabled_models


def test_forecasting_config_rejects_random_split() -> None:
    raw = _minimal_raw_config()
    raw["splitting"]["strategy"] = "random"

    with pytest.raises(ForecastingConfigurationError, match="chronological"):
        parse_forecasting_config(raw)


def test_forecasting_config_rejects_bad_output_root() -> None:
    raw = _minimal_raw_config()
    raw["forecasting"]["output_root"] = "data/raw/forecasting"

    with pytest.raises(ForecastingConfigurationError, match="outputs/passenger_forecasting"):
        parse_forecasting_config(raw)


def test_forecast_run_id_and_overrides_are_deterministic() -> None:
    config = load_forecasting_config("configs/passenger_forecasting_ci.yaml")
    updated = with_overrides(config, seed=99, output_root=Path("outputs/passenger_forecasting/test"), overwrite=True)

    assert updated.settings.seed == 99
    assert updated.settings.overwrite is True
    assert build_forecast_run_id(config, "validation-a") == build_forecast_run_id(config, "validation-a")
    assert build_forecast_run_id(config, "validation-a", "manual") == "manual"


def _minimal_raw_config() -> dict[str, object]:
    return {
        "forecasting": {
            "target": "expected_final_passengers",
            "prediction_horizon_days": 14,
            "minimum_history_days": 0,
            "output_root": "outputs/passenger_forecasting",
            "model_root": "outputs/models/passenger_forecasting",
            "report_root": "reports/passenger_forecasting",
            "overwrite": False,
            "seed": 1,
            "champion_selection_metric": "wape",
            "champion_selection_direction": "minimize",
            "minimum_improvement_over_baseline": 0.0,
        },
        "data": {
            "required_validation_status": ["passed"],
            "include_routes": [],
            "exclude_routes": [],
            "minimum_route_observations": 1,
            "allow_controlled_overbooking": True,
        },
        "splitting": {
            "strategy": "chronological",
            "train_fraction": 0.6,
            "validation_fraction": 0.2,
            "test_fraction": 0.2,
            "minimum_train_periods": 2,
            "gap_days": 0,
        },
        "features": {
            "use_route": True,
            "use_day_of_week": True,
            "use_month": True,
            "use_days_before_departure": True,
            "use_booked_passengers": True,
            "use_booking_velocity": True,
            "use_cancellations_to_date": True,
            "use_group_booking_count": True,
            "use_capacity": True,
            "use_demand_segment": True,
            "use_fare_class_mix": True,
            "use_historical_route_statistics": True,
            "historical_rolling_windows": [7],
        },
        "models": {
            "seasonal_naive": {"enabled": True},
            "historical_mean": {"enabled": True},
            "linear_regression": {"enabled": True},
        },
        "evaluation": {
            "metrics": ["mae", "rmse", "wape", "smape", "bias"],
            "evaluate_by_route": True,
            "evaluate_by_horizon": True,
            "evaluate_by_load_factor_band": True,
            "prediction_interval_levels": [0.8],
        },
    }
