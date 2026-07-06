"""Classification evaluation for flight-delay prediction."""

from __future__ import annotations

import math
from collections import defaultdict

from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig
from airline_operations_intelligence.delay_prediction.contracts import DelayModelRow


def evaluate_probabilities(rows: list[DelayModelRow], probabilities: list[float], threshold: float) -> dict[str, float]:
    """Calculate classification and probability metrics."""
    actual = [row.target for row in rows]
    predicted = [1 if probability >= threshold else 0 for probability in probabilities]
    tp = sum(1 for act, pred in zip(actual, predicted, strict=True) if act == 1 and pred == 1)
    fp = sum(1 for act, pred in zip(actual, predicted, strict=True) if act == 0 and pred == 1)
    tn = sum(1 for act, pred in zip(actual, predicted, strict=True) if act == 0 and pred == 0)
    fn = sum(1 for act, pred in zip(actual, predicted, strict=True) if act == 1 and pred == 0)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return {
        "row_count": float(len(rows)),
        "positive_count": float(sum(actual)),
        "negative_count": float(len(actual) - sum(actual)),
        "threshold": threshold,
        "tp": float(tp),
        "fp": float(fp),
        "tn": float(tn),
        "fn": float(fn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "balanced_accuracy": (recall + specificity) / 2,
        "predicted_positive_rate": sum(predicted) / len(predicted),
        "actual_positive_rate": sum(actual) / len(actual),
        "roc_auc": roc_auc(actual, probabilities),
        "pr_auc": pr_auc(actual, probabilities),
        "log_loss": log_loss(actual, probabilities),
        "brier_score": sum((probability - act) ** 2 for act, probability in zip(actual, probabilities, strict=True))
        / len(actual),
    }


def threshold_rows(
    rows: list[DelayModelRow], probabilities: list[float], config: DelayPredictionConfig
) -> list[dict[str, object]]:
    """Evaluate configured thresholds on validation data."""
    output: list[dict[str, object]] = []
    for threshold in config.settings.threshold_search_values:
        metrics = evaluate_probabilities(rows, probabilities, threshold)
        output.append({"threshold": threshold, **metrics})
    return output


def calibration_bins(rows: list[DelayModelRow], probabilities: list[float], bins: int) -> list[dict[str, object]]:
    """Return calibration bin statistics."""
    grouped: dict[int, list[tuple[DelayModelRow, float]]] = defaultdict(list)
    for row, probability in zip(rows, probabilities, strict=True):
        index = min(bins - 1, int(probability * bins))
        grouped[index].append((row, probability))
    output: list[dict[str, object]] = []
    for index in range(bins):
        pairs = grouped.get(index, [])
        if not pairs:
            output.append({"bin": index, "row_count": 0, "mean_probability": 0.0, "observed_delay_rate": 0.0})
            continue
        output.append(
            {
                "bin": index,
                "row_count": len(pairs),
                "mean_probability": sum(probability for _, probability in pairs) / len(pairs),
                "observed_delay_rate": sum(row.target for row, _ in pairs) / len(pairs),
            }
        )
    return output


def grouped_metrics(rows: list[DelayModelRow], probabilities: list[float], threshold: float) -> list[dict[str, object]]:
    """Calculate grouped classification metrics."""
    groups: dict[tuple[str, str], list[tuple[DelayModelRow, float]]] = defaultdict(list)
    for row, probability in zip(rows, probabilities, strict=True):
        groups[("route", row.route_id)].append((row, probability))
        groups[("origin_airport", row.origin_airport)].append((row, probability))
        groups[("time_band", _time_band(row.departure_hour))].append((row, probability))
        groups[("weather_exposure", str(bool(row.weather_exposure_flag)))].append((row, probability))
    output: list[dict[str, object]] = []
    for (dimension, value), pairs in sorted(groups.items()):
        metrics = evaluate_probabilities(
            [row for row, _ in pairs], [probability for _, probability in pairs], threshold
        )
        output.append({"dimension": dimension, "value": value, "sample_size": len(pairs), **metrics})
    return output


def roc_auc(actual: list[int], probabilities: list[float]) -> float:
    """Calculate ROC AUC with average ranks."""
    positives = sum(actual)
    negatives = len(actual) - positives
    if positives == 0 or negatives == 0:
        return 0.0
    sorted_pairs = sorted(zip(probabilities, actual, strict=True), key=lambda item: item[0])
    rank_sum = sum(index for index, (_, label) in enumerate(sorted_pairs, start=1) if label == 1)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def pr_auc(actual: list[int], probabilities: list[float]) -> float:
    """Calculate average precision style PR AUC."""
    positives = sum(actual)
    if positives == 0:
        return 0.0
    tp = 0
    area = 0.0
    for rank, (_, label) in enumerate(sorted(zip(probabilities, actual, strict=True), reverse=True), start=1):
        if label == 1:
            tp += 1
            area += tp / rank
    return area / positives


def log_loss(actual: list[int], probabilities: list[float]) -> float:
    """Calculate binary log loss."""
    eps = 1e-15
    return -sum(
        label * math.log(min(1 - eps, max(eps, probability)))
        + (1 - label) * math.log(min(1 - eps, max(eps, 1 - probability)))
        for label, probability in zip(actual, probabilities, strict=True)
    ) / len(actual)


def _safe_div(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _time_band(hour: int) -> str:
    if hour < 6:
        return "overnight"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"
