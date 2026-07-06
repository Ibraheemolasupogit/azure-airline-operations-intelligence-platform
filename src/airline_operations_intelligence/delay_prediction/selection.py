"""Champion and threshold selection for delay prediction."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import (
    DelayModelSelectionError,
    DelayThresholdSelectionError,
)
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig


def select_champion(
    validation_metrics: dict[str, dict[str, float]],
    model_roles: dict[str, str],
    config: DelayPredictionConfig,
) -> tuple[str, str]:
    """Select champion by configured metric with baseline fallback."""
    metric = config.settings.champion_selection_metric
    if not validation_metrics:
        raise DelayModelSelectionError("No validation metrics were available for champion selection.")
    ranked = sorted(
        validation_metrics,
        key=lambda model_id: (
            validation_metrics[model_id].get(metric, 0.0),
            validation_metrics[model_id].get("f1", 0.0),
            -validation_metrics[model_id].get("brier_score", 1.0),
            1 if model_roles[model_id] == "candidate" else 0,
            model_id,
        ),
        reverse=True,
    )
    champion = ranked[0]
    best_baseline = next((model_id for model_id in ranked if model_roles[model_id] == "baseline"), None)
    if best_baseline and model_roles[champion] == "candidate":
        uplift = validation_metrics[champion][metric] - validation_metrics[best_baseline][metric]
        if uplift < config.settings.minimum_improvement_over_baseline:
            champion = best_baseline
            return champion, f"Selected baseline because candidate uplift on {metric} was below configured minimum."
    return champion, f"Selected highest validation {metric} under deterministic tie-breakers."


def select_threshold(threshold_metrics: list[dict[str, object]], config: DelayPredictionConfig) -> tuple[float, str]:
    """Select classification threshold using validation metrics."""
    metric = config.settings.threshold_selection_metric
    if not threshold_metrics:
        raise DelayThresholdSelectionError("No threshold metrics were available.")
    ranked = sorted(
        threshold_metrics,
        key=lambda row: (
            _as_float(row.get(metric, 0.0)),
            _as_float(row.get("recall", 0.0)),
            _as_float(row.get("precision", 0.0)),
            -abs(_as_float(row["threshold"]) - config.settings.default_probability_threshold),
            -_as_float(row["threshold"]),
        ),
        reverse=True,
    )
    selected = _as_float(ranked[0]["threshold"])
    return selected, f"Selected threshold maximizing validation {metric} with recall/precision tie-breakers."


def _as_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
