"""Forecast evaluation metrics."""

from __future__ import annotations

import math
from collections import defaultdict

from airline_operations_intelligence.forecasting.contracts import ModelRow, Prediction


def evaluate_predictions(rows: list[ModelRow], predictions: list[Prediction]) -> dict[str, float]:
    """Calculate overall forecast metrics."""
    actual = [row.target for row in rows]
    predicted = [prediction.constrained_prediction for prediction in predictions]
    errors = [pred - act for pred, act in zip(predicted, actual, strict=True)]
    abs_errors = [abs(error) for error in errors]
    denominator = sum(abs(value) for value in actual)
    smape_terms = [
        0.0 if abs(act) + abs(pred) == 0 else 2 * abs(pred - act) / (abs(act) + abs(pred))
        for pred, act in zip(predicted, actual, strict=True)
    ]
    return {
        "mae": sum(abs_errors) / len(abs_errors),
        "rmse": math.sqrt(sum(error**2 for error in errors) / len(errors)),
        "wape": 0.0 if denominator == 0 else sum(abs_errors) / denominator,
        "smape": sum(smape_terms) / len(smape_terms),
        "bias": sum(errors) / len(errors),
        "underforecast_rate": sum(1 for error in errors if error < 0) / len(errors),
        "overforecast_rate": sum(1 for error in errors if error > 0) / len(errors),
    }


def grouped_metrics(rows: list[ModelRow], predictions: list[Prediction]) -> list[dict[str, object]]:
    """Calculate route-level and load-factor-band metrics."""
    output: list[dict[str, object]] = []
    by_route: dict[str, list[tuple[ModelRow, Prediction]]] = defaultdict(list)
    by_band: dict[str, list[tuple[ModelRow, Prediction]]] = defaultdict(list)
    for row, prediction in zip(rows, predictions, strict=True):
        by_route[row.route_id].append((row, prediction))
        by_band[_load_factor_band(row)].append((row, prediction))
    for dimension, groups in (("route", by_route), ("load_factor_band", by_band)):
        for value, pairs in sorted(groups.items()):
            metrics = evaluate_predictions([row for row, _ in pairs], [prediction for _, prediction in pairs])
            output.append({"dimension": dimension, "value": value, "sample_size": len(pairs), **metrics})
    return output


def _load_factor_band(row: ModelRow) -> str:
    load = row.target / row.seat_capacity
    if load < 0.75:
        return "low"
    if load < 0.9:
        return "medium"
    return "high"
