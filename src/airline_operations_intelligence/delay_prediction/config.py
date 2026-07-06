"""Configuration parsing for flight-delay prediction."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import DelayPredictionConfigurationError

DEFAULT_DELAY_PREDICTION_CONFIG_PATH = Path("configs/delay_prediction.yaml")
SUPPORTED_TARGETS = {"departure_delay_15_flag"}
SUPPORTED_METRICS = {
    "roc_auc",
    "pr_auc",
    "log_loss",
    "brier_score",
    "precision",
    "recall",
    "f1",
    "specificity",
    "balanced_accuracy",
}
SUPPORTED_MODELS = {"majority_class_baseline", "route_historical_rate_baseline", "logistic_regression"}
SUPPORTED_STATUSES = {"passed", "passed_with_warnings"}


@dataclass(frozen=True)
class RiskBand:
    """Probability interval assigned to a delay risk band."""

    name: str
    minimum_probability: float
    maximum_probability: float


@dataclass(frozen=True)
class DelayPredictionSettings:
    """Validated delay prediction settings."""

    target: str
    delay_threshold_minutes: int
    prediction_cutoff_minutes: int
    output_root: Path
    model_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    champion_selection_metric: str
    champion_selection_direction: str
    minimum_improvement_over_baseline: float
    enable_secondary_delay_regression: bool
    required_validation_status: tuple[str, ...]
    exclude_cancelled_flights: bool
    include_diverted_flights_with_valid_departure: bool
    minimum_training_rows: int
    minimum_positive_rows: int
    minimum_negative_rows: int
    allow_optional_passenger_forecast_input: bool
    train_fraction: float
    validation_fraction: float
    test_fraction: float
    minimum_train_rows: int
    minimum_validation_rows: int
    minimum_test_rows: int
    temporal_gap_days: int
    feature_flags: dict[str, bool]
    historical_windows: tuple[int, ...]
    enabled_models: tuple[str, ...]
    default_probability_threshold: float
    threshold_selection_metric: str
    threshold_search_values: tuple[float, ...]
    metrics: tuple[str, ...]
    evaluate_by_route: bool
    evaluate_by_origin_airport: bool
    evaluate_by_time_band: bool
    evaluate_by_weather_exposure: bool
    probability_bins: int
    risk_bands: tuple[RiskBand, ...]


@dataclass(frozen=True)
class DelayPredictionConfig:
    """Top-level delay prediction configuration."""

    settings: DelayPredictionSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "delay_prediction": {
                "target": s.target,
                "delay_threshold_minutes": s.delay_threshold_minutes,
                "prediction_cutoff_minutes": s.prediction_cutoff_minutes,
                "output_root": s.output_root.as_posix(),
                "model_root": s.model_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "champion_selection_metric": s.champion_selection_metric,
                "champion_selection_direction": s.champion_selection_direction,
                "minimum_improvement_over_baseline": s.minimum_improvement_over_baseline,
                "enable_secondary_delay_regression": s.enable_secondary_delay_regression,
            },
            "data": {
                "required_validation_status": list(s.required_validation_status),
                "exclude_cancelled_flights": s.exclude_cancelled_flights,
                "include_diverted_flights_with_valid_departure": s.include_diverted_flights_with_valid_departure,
                "minimum_training_rows": s.minimum_training_rows,
                "minimum_positive_rows": s.minimum_positive_rows,
                "minimum_negative_rows": s.minimum_negative_rows,
                "allow_optional_passenger_forecast_input": s.allow_optional_passenger_forecast_input,
            },
            "splitting": {
                "strategy": "chronological",
                "train_fraction": s.train_fraction,
                "validation_fraction": s.validation_fraction,
                "test_fraction": s.test_fraction,
                "minimum_train_rows": s.minimum_train_rows,
                "minimum_validation_rows": s.minimum_validation_rows,
                "minimum_test_rows": s.minimum_test_rows,
                "temporal_gap_days": s.temporal_gap_days,
            },
            "features": {**s.feature_flags, "historical_windows": list(s.historical_windows)},
            "models": {model: {"enabled": model in s.enabled_models} for model in SUPPORTED_MODELS},
            "classification": {
                "default_probability_threshold": s.default_probability_threshold,
                "threshold_selection_metric": s.threshold_selection_metric,
                "threshold_search_values": list(s.threshold_search_values),
            },
            "evaluation": {
                "metrics": list(s.metrics),
                "evaluate_by_route": s.evaluate_by_route,
                "evaluate_by_origin_airport": s.evaluate_by_origin_airport,
                "evaluate_by_time_band": s.evaluate_by_time_band,
                "evaluate_by_weather_exposure": s.evaluate_by_weather_exposure,
                "probability_bins": s.probability_bins,
            },
            "risk_bands": {
                band.name: {
                    "minimum_probability": band.minimum_probability,
                    "maximum_probability": band.maximum_probability,
                }
                for band in s.risk_bands
            },
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_delay_prediction_config(path: Path | str) -> DelayPredictionConfig:
    """Load delay prediction configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise DelayPredictionConfigurationError(f"Delay prediction configuration file not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DelayPredictionConfigurationError(
            f"Delay prediction configuration is not valid YAML: {config_path}"
        ) from exc
    if not isinstance(raw, dict):
        raise DelayPredictionConfigurationError("Delay prediction configuration root must be a mapping.")
    return parse_delay_prediction_config(raw)


def parse_delay_prediction_config(raw: dict[str, Any]) -> DelayPredictionConfig:
    """Validate raw delay prediction configuration."""
    delay = _mapping(raw, "delay_prediction")
    data = _mapping(raw, "data")
    splitting = _mapping(raw, "splitting")
    features = _mapping(raw, "features")
    models = _mapping(raw, "models")
    classification = _mapping(raw, "classification")
    evaluation = _mapping(raw, "evaluation")
    target = _choice(_str(delay.get("target"), "delay_prediction.target"), SUPPORTED_TARGETS, "delay_prediction.target")
    metrics = tuple(
        _choices(_strings(evaluation.get("metrics"), "evaluation.metrics"), SUPPORTED_METRICS, "evaluation.metrics")
    )
    champion_metric = _choice(
        _str(delay.get("champion_selection_metric"), "delay_prediction.champion_selection_metric"),
        SUPPORTED_METRICS,
        "delay_prediction.champion_selection_metric",
    )
    if champion_metric not in metrics:
        raise DelayPredictionConfigurationError("champion_selection_metric must be included in evaluation.metrics.")
    direction = _str(delay.get("champion_selection_direction"), "delay_prediction.champion_selection_direction")
    if direction != "maximize":
        raise DelayPredictionConfigurationError("Only champion_selection_direction=maximize is supported.")
    enabled_models = tuple(name for name, value in sorted(models.items()) if _model_enabled(name, value))
    unknown_models = sorted(set(models) - SUPPORTED_MODELS)
    if unknown_models:
        raise DelayPredictionConfigurationError(f"Unsupported model identifiers: {', '.join(unknown_models)}")
    if len(enabled_models) < 2:
        raise DelayPredictionConfigurationError("At least two delay models or baselines must be enabled.")
    required_statuses = tuple(
        _choices(
            _strings(data.get("required_validation_status"), "data.required_validation_status"),
            SUPPORTED_STATUSES,
            "data.required_validation_status",
        )
    )
    _reject_duplicates(required_statuses, "required validation statuses")
    feature_keys = (
        "use_route",
        "use_origin_airport",
        "use_destination_airport",
        "use_aircraft_type",
        "use_seat_capacity",
        "use_scheduled_block_minutes",
        "use_departure_hour",
        "use_day_of_week",
        "use_month",
        "use_weekend_flag",
        "use_service_type",
        "use_schedule_status",
        "use_predeparture_weather",
        "use_predeparture_airport_events",
        "use_predeparture_crew_state",
        "use_predeparture_aircraft_health",
        "use_historical_route_delay_features",
        "use_historical_airport_delay_features",
        "use_historical_aircraft_delay_features",
        "use_optional_passenger_forecast",
    )
    feature_flags = {key: _bool(features.get(key), f"features.{key}") for key in feature_keys}
    windows = tuple(
        sorted(
            {
                _positive_int(value, "features.historical_windows")
                for value in _list(features.get("historical_windows"), "features.historical_windows")
            }
        )
    )
    fractions = (
        _positive_float(splitting.get("train_fraction"), "splitting.train_fraction"),
        _positive_float(splitting.get("validation_fraction"), "splitting.validation_fraction"),
        _positive_float(splitting.get("test_fraction"), "splitting.test_fraction"),
    )
    if abs(sum(fractions) - 1.0) > 0.0001:
        raise DelayPredictionConfigurationError("Chronological split fractions must sum to 1.0.")
    if _str(splitting.get("strategy"), "splitting.strategy") != "chronological":
        raise DelayPredictionConfigurationError("Only chronological splitting is supported.")
    thresholds = tuple(
        sorted(
            {
                _probability(value, "classification.threshold_search_values")
                for value in _list(
                    classification.get("threshold_search_values"), "classification.threshold_search_values"
                )
            }
        )
    )
    if not thresholds:
        raise DelayPredictionConfigurationError("At least one threshold_search_value is required.")
    bands = _risk_bands(_mapping(raw, "risk_bands"))
    settings = DelayPredictionSettings(
        target=target,
        delay_threshold_minutes=_non_negative_int(
            delay.get("delay_threshold_minutes"), "delay_prediction.delay_threshold_minutes"
        ),
        prediction_cutoff_minutes=_positive_int(
            delay.get("prediction_cutoff_minutes"), "delay_prediction.prediction_cutoff_minutes"
        ),
        output_root=_root(delay.get("output_root"), ("outputs", "delay_prediction")),
        model_root=_root(delay.get("model_root"), ("outputs", "models", "delay_prediction")),
        report_root=_root(delay.get("report_root"), ("reports", "delay_prediction")),
        overwrite=_bool(delay.get("overwrite"), "delay_prediction.overwrite"),
        seed=_non_negative_int(delay.get("seed"), "delay_prediction.seed"),
        champion_selection_metric=champion_metric,
        champion_selection_direction=direction,
        minimum_improvement_over_baseline=_non_negative_float(
            delay.get("minimum_improvement_over_baseline"), "delay_prediction.minimum_improvement_over_baseline"
        ),
        enable_secondary_delay_regression=_bool(
            delay.get("enable_secondary_delay_regression"), "delay_prediction.enable_secondary_delay_regression"
        ),
        required_validation_status=required_statuses,
        exclude_cancelled_flights=_bool(data.get("exclude_cancelled_flights"), "data.exclude_cancelled_flights"),
        include_diverted_flights_with_valid_departure=_bool(
            data.get("include_diverted_flights_with_valid_departure"),
            "data.include_diverted_flights_with_valid_departure",
        ),
        minimum_training_rows=_positive_int(data.get("minimum_training_rows"), "data.minimum_training_rows"),
        minimum_positive_rows=_positive_int(data.get("minimum_positive_rows"), "data.minimum_positive_rows"),
        minimum_negative_rows=_positive_int(data.get("minimum_negative_rows"), "data.minimum_negative_rows"),
        allow_optional_passenger_forecast_input=_bool(
            data.get("allow_optional_passenger_forecast_input"), "data.allow_optional_passenger_forecast_input"
        ),
        train_fraction=fractions[0],
        validation_fraction=fractions[1],
        test_fraction=fractions[2],
        minimum_train_rows=_positive_int(splitting.get("minimum_train_rows"), "splitting.minimum_train_rows"),
        minimum_validation_rows=_positive_int(
            splitting.get("minimum_validation_rows"), "splitting.minimum_validation_rows"
        ),
        minimum_test_rows=_positive_int(splitting.get("minimum_test_rows"), "splitting.minimum_test_rows"),
        temporal_gap_days=_non_negative_int(splitting.get("temporal_gap_days"), "splitting.temporal_gap_days"),
        feature_flags=feature_flags,
        historical_windows=windows,
        enabled_models=enabled_models,
        default_probability_threshold=_probability(
            classification.get("default_probability_threshold"), "classification.default_probability_threshold"
        ),
        threshold_selection_metric=_choice(
            _str(classification.get("threshold_selection_metric"), "classification.threshold_selection_metric"),
            SUPPORTED_METRICS,
            "classification.threshold_selection_metric",
        ),
        threshold_search_values=thresholds,
        metrics=metrics,
        evaluate_by_route=_bool(evaluation.get("evaluate_by_route"), "evaluation.evaluate_by_route"),
        evaluate_by_origin_airport=_bool(
            evaluation.get("evaluate_by_origin_airport"), "evaluation.evaluate_by_origin_airport"
        ),
        evaluate_by_time_band=_bool(evaluation.get("evaluate_by_time_band"), "evaluation.evaluate_by_time_band"),
        evaluate_by_weather_exposure=_bool(
            evaluation.get("evaluate_by_weather_exposure"), "evaluation.evaluate_by_weather_exposure"
        ),
        probability_bins=_positive_int(evaluation.get("probability_bins"), "evaluation.probability_bins"),
        risk_bands=bands,
    )
    return DelayPredictionConfig(settings=settings)


def with_overrides(
    config: DelayPredictionConfig,
    *,
    output_root: Path | None = None,
    model_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    delay_threshold_minutes: int | None = None,
    prediction_cutoff_minutes: int | None = None,
    overwrite: bool | None = None,
) -> DelayPredictionConfig:
    """Return config with CLI overrides applied."""
    s = config.settings
    return DelayPredictionConfig(
        settings=DelayPredictionSettings(
            **{
                **s.__dict__,
                "output_root": output_root if output_root is not None else s.output_root,
                "model_root": model_root if model_root is not None else s.model_root,
                "report_root": report_root if report_root is not None else s.report_root,
                "seed": seed if seed is not None else s.seed,
                "delay_threshold_minutes": delay_threshold_minutes
                if delay_threshold_minutes is not None
                else s.delay_threshold_minutes,
                "prediction_cutoff_minutes": prediction_cutoff_minutes
                if prediction_cutoff_minutes is not None
                else s.prediction_cutoff_minutes,
                "overwrite": overwrite if overwrite is not None else s.overwrite,
            }
        )
    )


def build_delay_run_id(
    config: DelayPredictionConfig, validation_run_id: str, forecast_run_id: str | None, explicit_run_id: str | None
) -> str:
    """Build deterministic delay prediction run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise DelayPredictionConfigurationError(
                "delay_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = f"{validation_run_id}|{forecast_run_id or 'no-forecast'}|{config.fingerprint()}"
    return f"delay-{validation_run_id}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _risk_bands(raw: dict[str, Any]) -> tuple[RiskBand, ...]:
    bands = tuple(
        RiskBand(
            name=name,
            minimum_probability=_probability(
                _mapping(value, f"risk_bands.{name}").get("minimum_probability"),
                f"risk_bands.{name}.minimum_probability",
            ),
            maximum_probability=_probability(
                _mapping(value, f"risk_bands.{name}").get("maximum_probability"),
                f"risk_bands.{name}.maximum_probability",
            ),
        )
        for name, value in sorted(
            raw.items(),
            key=lambda item: _probability(
                _mapping(item[1], f"risk_bands.{item[0]}").get("minimum_probability"),
                f"risk_bands.{item[0]}.minimum_probability",
            ),
        )
    )
    if not bands:
        raise DelayPredictionConfigurationError("At least one risk band is required.")
    if abs(bands[0].minimum_probability - 0.0) > 0.0001 or abs(bands[-1].maximum_probability - 1.0) > 0.0001:
        raise DelayPredictionConfigurationError("Risk bands must cover probabilities from 0.0 through 1.0.")
    previous = 0.0
    for band in bands:
        if abs(band.minimum_probability - previous) > 0.0001 or band.maximum_probability <= band.minimum_probability:
            raise DelayPredictionConfigurationError("Risk bands must be contiguous and increasing.")
        previous = band.maximum_probability
    return bands


def _mapping(raw: object, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DelayPredictionConfigurationError(f"{label} must be a mapping.")
    value = raw.get(label) if "." not in label else raw
    if not isinstance(value, dict):
        raise DelayPredictionConfigurationError(f"{label} must be a mapping.")
    return value


def _list(raw: object, label: str) -> list[Any]:
    if not isinstance(raw, list):
        raise DelayPredictionConfigurationError(f"{label} must be a list.")
    return raw


def _str(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise DelayPredictionConfigurationError(f"{label} must be a non-empty string.")
    return raw


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise DelayPredictionConfigurationError(f"{label} must be boolean.")
    return raw


def _strings(raw: object, label: str) -> list[str]:
    values = _list(raw, label)
    if not all(isinstance(value, str) and value for value in values):
        raise DelayPredictionConfigurationError(f"{label} must contain non-empty strings.")
    return values


def _choice(value: str, choices: set[str], label: str) -> str:
    if value not in choices:
        raise DelayPredictionConfigurationError(f"{label} must be one of: {', '.join(sorted(choices))}.")
    return value


def _choices(values: list[str], choices: set[str], label: str) -> list[str]:
    return [_choice(value, choices, label) for value in values]


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise DelayPredictionConfigurationError(f"Duplicate {label} are not allowed.")


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0:
        raise DelayPredictionConfigurationError(f"{label} must be a positive integer.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise DelayPredictionConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _positive_float(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or float(raw) <= 0:
        raise DelayPredictionConfigurationError(f"{label} must be a positive number.")
    return float(raw)


def _non_negative_float(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or float(raw) < 0:
        raise DelayPredictionConfigurationError(f"{label} must be a non-negative number.")
    return float(raw)


def _probability(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or not 0 <= float(raw) <= 1:
        raise DelayPredictionConfigurationError(f"{label} must be a probability between 0 and 1.")
    return float(raw)


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    value = _str(raw, ".".join(allowed_prefix))
    path = Path(value)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise DelayPredictionConfigurationError(f"{value} must remain under {'/'.join(allowed_prefix)}.")
    return path


def _model_enabled(name: str, raw: object) -> bool:
    model = _mapping(raw, f"models.{name}")
    return _bool(model.get("enabled"), f"models.{name}.enabled")
