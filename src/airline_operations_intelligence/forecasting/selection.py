"""Champion model selection."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import ModelSelectionError
from airline_operations_intelligence.forecasting.config import ForecastingConfig


def select_champion(
    validation_metrics: dict[str, dict[str, float]],
    model_roles: dict[str, str],
    config: ForecastingConfig,
) -> tuple[str, str]:
    """Select champion using deterministic validation-only criteria."""
    if not validation_metrics:
        raise ModelSelectionError("No model validation metrics were available for champion selection.")
    metric = config.settings.champion_selection_metric
    baseline_ids = sorted(model_id for model_id, role in model_roles.items() if role == "baseline")
    best_baseline = min(baseline_ids, key=lambda model_id: (validation_metrics[model_id][metric], model_id))
    best_baseline_score = validation_metrics[best_baseline][metric]
    ranked = sorted(
        validation_metrics,
        key=lambda model_id: (
            validation_metrics[model_id][metric],
            abs(validation_metrics[model_id].get("bias", 0.0)),
            validation_metrics[model_id].get("mae", 0.0),
            0 if model_roles[model_id] == "baseline" else 1,
            model_id,
        ),
    )
    best = ranked[0]
    required_score = best_baseline_score * (1 - config.settings.minimum_improvement_over_baseline)
    if model_roles[best] != "baseline" and validation_metrics[best][metric] > required_score:
        rationale = (
            f"Selected baseline {best_baseline}; best candidate did not meet configured improvement over baseline."
        )
        return best_baseline, rationale
    rationale = (
        f"Selected {best} by validation {metric}={validation_metrics[best][metric]:.6f}; "
        f"best baseline was {best_baseline} with {metric}={best_baseline_score:.6f}."
    )
    return best, rationale
