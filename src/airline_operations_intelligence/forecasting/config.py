"""Configuration parsing for passenger-demand forecasting."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import ForecastingConfigurationError

DEFAULT_FORECASTING_CONFIG_PATH = Path("configs/passenger_forecasting.yaml")
SUPPORTED_TARGETS = {"expected_final_passengers"}
SUPPORTED_METRICS = {"mae", "rmse", "wape", "smape", "bias"}
SUPPORTED_MODELS = {"seasonal_naive", "historical_mean", "linear_regression"}
SUPPORTED_STATUSES = {"passed", "passed_with_warnings"}


@dataclass(frozen=True)
class ForecastingSettings:
    """Validated passenger forecasting settings."""

    target: str
    prediction_horizon_days: int
    minimum_history_days: int
    output_root: Path
    model_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    champion_selection_metric: str
    champion_selection_direction: str
    minimum_improvement_over_baseline: float
    required_validation_status: tuple[str, ...]
    include_routes: tuple[str, ...]
    exclude_routes: tuple[str, ...]
    minimum_route_observations: int
    allow_controlled_overbooking: bool
    train_fraction: float
    validation_fraction: float
    test_fraction: float
    minimum_train_periods: int
    gap_days: int
    feature_flags: dict[str, bool]
    historical_rolling_windows: tuple[int, ...]
    enabled_models: tuple[str, ...]
    metrics: tuple[str, ...]
    evaluate_by_route: bool
    evaluate_by_horizon: bool
    evaluate_by_load_factor_band: bool
    prediction_interval_levels: tuple[float, ...]


@dataclass(frozen=True)
class ForecastingConfig:
    """Top-level passenger forecasting configuration."""

    settings: ForecastingSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "forecasting": {
                "target": s.target,
                "prediction_horizon_days": s.prediction_horizon_days,
                "minimum_history_days": s.minimum_history_days,
                "output_root": s.output_root.as_posix(),
                "model_root": s.model_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "champion_selection_metric": s.champion_selection_metric,
                "champion_selection_direction": s.champion_selection_direction,
                "minimum_improvement_over_baseline": s.minimum_improvement_over_baseline,
            },
            "data": {
                "required_validation_status": list(s.required_validation_status),
                "include_routes": list(s.include_routes),
                "exclude_routes": list(s.exclude_routes),
                "minimum_route_observations": s.minimum_route_observations,
                "allow_controlled_overbooking": s.allow_controlled_overbooking,
            },
            "splitting": {
                "strategy": "chronological",
                "train_fraction": s.train_fraction,
                "validation_fraction": s.validation_fraction,
                "test_fraction": s.test_fraction,
                "minimum_train_periods": s.minimum_train_periods,
                "gap_days": s.gap_days,
            },
            "features": {
                **s.feature_flags,
                "historical_rolling_windows": list(s.historical_rolling_windows),
            },
            "models": {model: {"enabled": model in s.enabled_models} for model in SUPPORTED_MODELS},
            "evaluation": {
                "metrics": list(s.metrics),
                "evaluate_by_route": s.evaluate_by_route,
                "evaluate_by_horizon": s.evaluate_by_horizon,
                "evaluate_by_load_factor_band": s.evaluate_by_load_factor_band,
                "prediction_interval_levels": list(s.prediction_interval_levels),
            },
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_forecasting_config(path: Path | str) -> ForecastingConfig:
    """Load forecasting configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise ForecastingConfigurationError(f"Forecasting configuration file not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ForecastingConfigurationError(f"Forecasting configuration is not valid YAML: {config_path}") from exc
    if not isinstance(raw, dict):
        raise ForecastingConfigurationError("Forecasting configuration root must be a mapping.")
    return parse_forecasting_config(raw)


def parse_forecasting_config(raw: dict[str, Any]) -> ForecastingConfig:
    """Validate raw forecasting configuration."""
    forecasting = _mapping(raw, "forecasting")
    data = _mapping(raw, "data")
    splitting = _mapping(raw, "splitting")
    features = _mapping(raw, "features")
    models = _mapping(raw, "models")
    evaluation = _mapping(raw, "evaluation")
    target = _choice(_str(forecasting.get("target"), "forecasting.target"), SUPPORTED_TARGETS, "forecasting.target")
    metrics = tuple(
        _choices(_strings(evaluation.get("metrics"), "evaluation.metrics"), SUPPORTED_METRICS, "evaluation.metrics")
    )
    champion_metric = _choice(
        _str(forecasting.get("champion_selection_metric"), "forecasting.champion_selection_metric"),
        SUPPORTED_METRICS,
        "forecasting.champion_selection_metric",
    )
    if champion_metric not in metrics:
        raise ForecastingConfigurationError("champion_selection_metric must be included in evaluation.metrics.")
    enabled_models = tuple(name for name, value in sorted(models.items()) if _model_enabled(name, value))
    if len(enabled_models) < 2:
        raise ForecastingConfigurationError("At least two models or baselines must be enabled.")
    unknown_models = sorted(set(models) - SUPPORTED_MODELS)
    if unknown_models:
        raise ForecastingConfigurationError(f"Unsupported model identifiers: {', '.join(unknown_models)}")
    required_statuses = tuple(
        _choices(
            _strings(data.get("required_validation_status"), "data.required_validation_status"),
            SUPPORTED_STATUSES,
            "data.required_validation_status",
        )
    )
    _reject_duplicates(required_statuses, "required validation statuses")
    feature_flags = {
        key: _bool(features.get(key), f"features.{key}")
        for key in (
            "use_route",
            "use_day_of_week",
            "use_month",
            "use_days_before_departure",
            "use_booked_passengers",
            "use_booking_velocity",
            "use_cancellations_to_date",
            "use_group_booking_count",
            "use_capacity",
            "use_demand_segment",
            "use_fare_class_mix",
            "use_historical_route_statistics",
        )
    }
    windows = tuple(
        sorted(
            {
                _positive_int(value, "features.historical_rolling_windows")
                for value in _list(features.get("historical_rolling_windows"), "features.historical_rolling_windows")
            }
        )
    )
    fractions = (
        _positive_float(splitting.get("train_fraction"), "splitting.train_fraction"),
        _positive_float(splitting.get("validation_fraction"), "splitting.validation_fraction"),
        _positive_float(splitting.get("test_fraction"), "splitting.test_fraction"),
    )
    if abs(sum(fractions) - 1.0) > 0.0001:
        raise ForecastingConfigurationError("Chronological split fractions must sum to 1.0.")
    strategy = _str(splitting.get("strategy"), "splitting.strategy")
    if strategy != "chronological":
        raise ForecastingConfigurationError("Only chronological splitting is supported.")
    direction = _str(forecasting.get("champion_selection_direction"), "forecasting.champion_selection_direction")
    if direction != "minimize":
        raise ForecastingConfigurationError("Only champion_selection_direction=minimize is supported.")
    levels = tuple(
        sorted(
            {
                _probability(value, "evaluation.prediction_interval_levels")
                for value in _list(
                    evaluation.get("prediction_interval_levels"), "evaluation.prediction_interval_levels"
                )
            }
        )
    )
    if not levels or any(level <= 0 or level >= 1 for level in levels):
        raise ForecastingConfigurationError("Prediction interval levels must be between 0 and 1.")
    settings = ForecastingSettings(
        target=target,
        prediction_horizon_days=_positive_int(
            forecasting.get("prediction_horizon_days"), "forecasting.prediction_horizon_days"
        ),
        minimum_history_days=_non_negative_int(
            forecasting.get("minimum_history_days"), "forecasting.minimum_history_days"
        ),
        output_root=_root(forecasting.get("output_root"), ("outputs", "passenger_forecasting")),
        model_root=_root(forecasting.get("model_root"), ("outputs", "models", "passenger_forecasting")),
        report_root=_root(forecasting.get("report_root"), ("reports", "passenger_forecasting")),
        overwrite=_bool(forecasting.get("overwrite"), "forecasting.overwrite"),
        seed=_non_negative_int(forecasting.get("seed"), "forecasting.seed"),
        champion_selection_metric=champion_metric,
        champion_selection_direction=direction,
        minimum_improvement_over_baseline=_non_negative_float(
            forecasting.get("minimum_improvement_over_baseline"),
            "forecasting.minimum_improvement_over_baseline",
        ),
        required_validation_status=required_statuses,
        include_routes=tuple(_strings(data.get("include_routes"), "data.include_routes")),
        exclude_routes=tuple(_strings(data.get("exclude_routes"), "data.exclude_routes")),
        minimum_route_observations=_positive_int(
            data.get("minimum_route_observations"), "data.minimum_route_observations"
        ),
        allow_controlled_overbooking=_bool(
            data.get("allow_controlled_overbooking"), "data.allow_controlled_overbooking"
        ),
        train_fraction=fractions[0],
        validation_fraction=fractions[1],
        test_fraction=fractions[2],
        minimum_train_periods=_positive_int(splitting.get("minimum_train_periods"), "splitting.minimum_train_periods"),
        gap_days=_non_negative_int(splitting.get("gap_days"), "splitting.gap_days"),
        feature_flags=feature_flags,
        historical_rolling_windows=windows,
        enabled_models=enabled_models,
        metrics=metrics,
        evaluate_by_route=_bool(evaluation.get("evaluate_by_route"), "evaluation.evaluate_by_route"),
        evaluate_by_horizon=_bool(evaluation.get("evaluate_by_horizon"), "evaluation.evaluate_by_horizon"),
        evaluate_by_load_factor_band=_bool(
            evaluation.get("evaluate_by_load_factor_band"), "evaluation.evaluate_by_load_factor_band"
        ),
        prediction_interval_levels=levels,
    )
    return ForecastingConfig(settings=settings)


def with_overrides(
    config: ForecastingConfig,
    *,
    output_root: Path | None = None,
    model_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    prediction_horizon_days: int | None = None,
    overwrite: bool | None = None,
) -> ForecastingConfig:
    """Return a copy of config with explicit CLI overrides."""
    current = config.settings
    return ForecastingConfig(
        settings=ForecastingSettings(
            **{
                **current.__dict__,
                "output_root": current.output_root
                if output_root is None
                else _root(output_root, ("outputs", "passenger_forecasting")),
                "model_root": current.model_root
                if model_root is None
                else _root(model_root, ("outputs", "models", "passenger_forecasting")),
                "report_root": current.report_root
                if report_root is None
                else _root(report_root, ("reports", "passenger_forecasting")),
                "seed": current.seed if seed is None else _non_negative_int(seed, "seed"),
                "prediction_horizon_days": current.prediction_horizon_days
                if prediction_horizon_days is None
                else _positive_int(prediction_horizon_days, "prediction_horizon_days"),
                "overwrite": current.overwrite if overwrite is None else overwrite,
            }
        )
    )


def build_forecast_run_id(config: ForecastingConfig, validation_run_id: str, explicit_run_id: str | None = None) -> str:
    """Build deterministic filesystem-safe forecast run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", explicit_run_id):
            raise ForecastingConfigurationError("forecast_run_id may contain only letters, numbers, '.', '_', '-'.")
        return explicit_run_id
    return f"pf-{validation_run_id}-{config.settings.prediction_horizon_days}d-{config.fingerprint()[:10]}"


def _mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ForecastingConfigurationError(f"{key} must be present and must be a mapping.")
    return value


def _str(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ForecastingConfigurationError(f"{key} must be a non-empty string.")
    return value


def _bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise ForecastingConfigurationError(f"{key} must be a boolean.")
    return value


def _list(value: Any, key: str) -> list[Any]:
    if not isinstance(value, list):
        raise ForecastingConfigurationError(f"{key} must be a list.")
    return value


def _strings(value: Any, key: str) -> list[str]:
    values = _list(value, key)
    if not all(isinstance(item, str) for item in values):
        raise ForecastingConfigurationError(f"{key} must contain strings.")
    return values


def _positive_int(value: Any, key: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ForecastingConfigurationError(f"{key} must be a positive integer.")
    return value


def _non_negative_int(value: Any, key: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ForecastingConfigurationError(f"{key} must be a non-negative integer.")
    return value


def _positive_float(value: Any, key: str) -> float:
    if not isinstance(value, int | float) or float(value) <= 0:
        raise ForecastingConfigurationError(f"{key} must be a positive number.")
    return float(value)


def _non_negative_float(value: Any, key: str) -> float:
    if not isinstance(value, int | float) or float(value) < 0:
        raise ForecastingConfigurationError(f"{key} must be a non-negative number.")
    return float(value)


def _probability(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise ForecastingConfigurationError(f"{key} must be numeric.")
    number = float(value)
    if number <= 0 or number >= 1:
        raise ForecastingConfigurationError(f"{key} must be between 0 and 1.")
    return number


def _choice(value: str, choices: set[str], key: str) -> str:
    if value not in choices:
        raise ForecastingConfigurationError(f"{key} must be one of {sorted(choices)}.")
    return value


def _choices(values: list[str], choices: set[str], key: str) -> list[str]:
    unknown = sorted(set(values) - choices)
    if unknown:
        raise ForecastingConfigurationError(f"{key} contains unsupported values: {', '.join(unknown)}.")
    _reject_duplicates(tuple(values), key)
    return values


def _model_enabled(name: str, value: Any) -> bool:
    if name not in SUPPORTED_MODELS:
        return False
    if not isinstance(value, dict):
        raise ForecastingConfigurationError(f"models.{name} must be a mapping.")
    return _bool(value.get("enabled"), f"models.{name}.enabled")


def _root(value: Any, expected_prefix: tuple[str, ...]) -> Path:
    root = Path(_str(str(value), "/".join(expected_prefix)))
    if root.is_absolute() or ".." in root.parts:
        raise ForecastingConfigurationError(f"{root} must be repository-relative and cannot contain '..'.")
    if len(root.parts) < len(expected_prefix) or root.parts[: len(expected_prefix)] != expected_prefix:
        raise ForecastingConfigurationError(f"{root} must be under {'/'.join(expected_prefix)}.")
    return Path(*root.parts)


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ForecastingConfigurationError(f"Duplicate {label}: {value}")
        seen.add(value)
