"""Empirical prediction interval helpers."""

from __future__ import annotations

from airline_operations_intelligence.forecasting.contracts import ModelRow, Prediction


def residual_quantiles(
    rows: list[ModelRow], predictions: list[Prediction], levels: tuple[float, ...]
) -> dict[str, float]:
    """Calculate absolute residual quantiles from validation predictions."""
    residuals = sorted(
        abs(pred.constrained_prediction - row.target) for row, pred in zip(rows, predictions, strict=True)
    )
    if not residuals:
        return {f"{int(level * 100)}": 0.0 for level in levels}
    quantiles: dict[str, float] = {}
    for level in levels:
        index = min(len(residuals) - 1, max(0, round(level * (len(residuals) - 1))))
        quantiles[f"{int(level * 100)}"] = residuals[index]
    return quantiles


def interval_bounds(prediction: float, quantiles: dict[str, float]) -> dict[str, float]:
    """Build ordered non-negative prediction interval bounds."""
    bounds: dict[str, float] = {}
    for level, width in sorted(quantiles.items()):
        bounds[f"lower_{level}"] = max(0.0, round(prediction - width))
        bounds[f"upper_{level}"] = max(round(prediction), round(prediction + width))
    return bounds
