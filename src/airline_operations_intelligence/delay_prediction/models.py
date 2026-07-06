"""Deterministic baselines and lightweight classifier for flight-delay prediction."""

from __future__ import annotations

import math

from airline_operations_intelligence.common.exceptions import DelayTrainingError
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig
from airline_operations_intelligence.delay_prediction.contracts import DelayModel, DelayModelRow


def train_model(model_id: str, train_rows: list[DelayModelRow], config: DelayPredictionConfig) -> DelayModel:
    """Train a deterministic delay classifier."""
    if not train_rows:
        raise DelayTrainingError("Delay model training requires at least one row.")
    global_rate = sum(row.target for row in train_rows) / len(train_rows)
    global_mean_delay = sum(row.delay_minutes for row in train_rows) / len(train_rows)
    route_rates = _route_rates(train_rows)
    route_mean_delay = _route_mean_delay(train_rows)
    if model_id == "majority_class_baseline":
        return DelayModel(
            model_id=model_id,
            model_role="baseline",
            parameters={"strategy": "training_prevalence"},
            feature_names=[],
            category_levels={},
            coefficients={},
            route_rates=route_rates,
            route_mean_delay=route_mean_delay,
            global_rate=global_rate,
            global_mean_delay=global_mean_delay,
        )
    if model_id == "route_historical_rate_baseline":
        return DelayModel(
            model_id=model_id,
            model_role="baseline",
            parameters={"strategy": "training_route_delay_rate_with_global_fallback"},
            feature_names=["route_id"],
            category_levels={},
            coefficients={},
            route_rates=route_rates,
            route_mean_delay=route_mean_delay,
            global_rate=global_rate,
            global_mean_delay=global_mean_delay,
        )
    if model_id == "logistic_regression":
        feature_names, category_levels = _feature_schema(train_rows)
        return DelayModel(
            model_id=model_id,
            model_role="candidate",
            parameters={
                "algorithm": "deterministic_gradient_descent_logistic_regression",
                "epochs": 600,
                "seed": config.settings.seed,
            },
            feature_names=feature_names,
            category_levels=category_levels,
            coefficients=_fit_logistic(train_rows, feature_names, category_levels, config.settings.seed),
            route_rates=route_rates,
            route_mean_delay=route_mean_delay,
            global_rate=global_rate,
            global_mean_delay=global_mean_delay,
        )
    raise DelayTrainingError(f"Unsupported delay model_id: {model_id}")


def predict_probability(model: DelayModel, rows: list[DelayModelRow]) -> list[float]:
    """Predict delay probabilities."""
    probabilities: list[float] = []
    for row in rows:
        if model.model_id == "majority_class_baseline":
            probability = model.global_rate
        elif model.model_id == "route_historical_rate_baseline":
            probability = model.route_rates.get(row.route_id, model.global_rate)
        else:
            vector = _vector(row, model.feature_names, model.category_levels)
            logit = model.coefficients.get("__intercept__", 0.0) + sum(
                model.coefficients.get(name, 0.0) * value for name, value in vector.items()
            )
            probability = _sigmoid(logit)
        probabilities.append(min(0.999999, max(0.000001, probability)))
    return probabilities


def estimate_delay_minutes(model: DelayModel, rows: list[DelayModelRow], probabilities: list[float]) -> list[float]:
    """Estimate non-negative delay minutes from training route means and probability."""
    estimates: list[float] = []
    for row, probability in zip(rows, probabilities, strict=True):
        route_delay = model.route_mean_delay.get(row.route_id, model.global_mean_delay)
        estimates.append(round(max(0.0, route_delay * (0.5 + probability)), 4))
    return estimates


def _route_rates(rows: list[DelayModelRow]) -> dict[str, float]:
    values: dict[str, list[int]] = {}
    for row in rows:
        values.setdefault(row.route_id, []).append(row.target)
    return {route: sum(items) / len(items) for route, items in sorted(values.items())}


def _route_mean_delay(rows: list[DelayModelRow]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in rows:
        values.setdefault(row.route_id, []).append(row.delay_minutes)
    return {route: sum(items) / len(items) for route, items in sorted(values.items())}


def _feature_schema(rows: list[DelayModelRow]) -> tuple[list[str], dict[str, list[str]]]:
    numeric: set[str] = set()
    categories: dict[str, set[str]] = {}
    for row in rows:
        for name, value in row.features.items():
            if isinstance(value, str):
                categories.setdefault(name, set()).add(value)
            else:
                numeric.add(name)
    feature_names = sorted(numeric) + [
        f"{name}={level}" for name in sorted(categories) for level in sorted(categories[name])
    ]
    return feature_names, {name: sorted(values) for name, values in categories.items()}


def _vector(row: DelayModelRow, feature_names: list[str], category_levels: dict[str, list[str]]) -> dict[str, float]:
    vector = {name: 0.0 for name in feature_names}
    for name, value in row.features.items():
        if isinstance(value, str):
            encoded = f"{name}={value}"
            if encoded in vector:
                vector[encoded] = 1.0
        elif name in vector:
            vector[name] = float(value)
    return vector


def _fit_logistic(
    rows: list[DelayModelRow],
    feature_names: list[str],
    category_levels: dict[str, list[str]],
    seed: int,
) -> dict[str, float]:
    coefficients = {name: 0.0 for name in feature_names}
    prevalence = min(0.999, max(0.001, sum(row.target for row in rows) / len(rows)))
    coefficients["__intercept__"] = math.log(prevalence / (1 - prevalence))
    learning_rate = 0.08 + seed * 0.0
    scale = {
        name: max(
            1.0, math.sqrt(sum(_vector(row, feature_names, category_levels)[name] ** 2 for row in rows) / len(rows))
        )
        for name in feature_names
    }
    for _ in range(600):
        gradients = {name: 0.0 for name in coefficients}
        for row in rows:
            vector = _vector(row, feature_names, category_levels)
            logit = coefficients["__intercept__"] + sum(
                coefficients[name] * (value / scale[name]) for name, value in vector.items()
            )
            error = _sigmoid(logit) - row.target
            gradients["__intercept__"] += error
            for name, value in vector.items():
                gradients[name] += error * (value / scale[name])
        for name in coefficients:
            coefficients[name] -= learning_rate * gradients[name] / len(rows)
    return {name: round(value / scale.get(name, 1.0), 10) for name, value in coefficients.items()}


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)
