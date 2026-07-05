"""Deterministic passenger-demand baselines and lightweight model training."""

from __future__ import annotations

import math

from airline_operations_intelligence.forecasting.config import ForecastingConfig
from airline_operations_intelligence.forecasting.contracts import ModelRow, Prediction, TrainedModel


def train_model(model_id: str, train_rows: list[ModelRow], config: ForecastingConfig) -> TrainedModel:
    """Train a deterministic baseline or linear model."""
    route_means = _route_means(train_rows)
    global_mean = sum(row.target for row in train_rows) / len(train_rows)
    route_conversion = _route_conversion(train_rows)
    global_conversion = sum(row.target / max(1, row.booked_passengers) for row in train_rows) / len(train_rows)
    if model_id == "historical_mean":
        return TrainedModel(
            model_id=model_id,
            model_role="baseline",
            parameters={"strategy": "prior_route_mean_with_global_fallback"},
            feature_names=["route_id"],
            category_levels={},
            coefficients={},
            route_means=route_means,
            global_mean=global_mean,
            route_conversion=route_conversion,
            global_conversion=global_conversion,
        )
    if model_id == "seasonal_naive":
        return TrainedModel(
            model_id=model_id,
            model_role="baseline",
            parameters={"strategy": "horizon_bookings_times_prior_route_conversion"},
            feature_names=["booked_passengers", "route_id"],
            category_levels={},
            coefficients={},
            route_means=route_means,
            global_mean=global_mean,
            route_conversion=route_conversion,
            global_conversion=global_conversion,
        )
    if model_id == "linear_regression":
        feature_names, category_levels = _feature_schema(train_rows)
        coefficients = _fit_linear_gradient_descent(train_rows, feature_names, category_levels, config.settings.seed)
        return TrainedModel(
            model_id=model_id,
            model_role="candidate",
            parameters={
                "algorithm": "deterministic_gradient_descent_linear_regression",
                "epochs": 700,
                "seed": config.settings.seed,
            },
            feature_names=feature_names,
            category_levels=category_levels,
            coefficients=coefficients,
            route_means=route_means,
            global_mean=global_mean,
            route_conversion=route_conversion,
            global_conversion=global_conversion,
        )
    raise ValueError(f"Unsupported model_id: {model_id}")


def predict(model: TrainedModel, rows: list[ModelRow]) -> list[Prediction]:
    """Predict passenger demand for rows."""
    predictions: list[Prediction] = []
    for row in rows:
        if model.model_id == "historical_mean":
            raw = model.route_means.get(row.route_id, model.global_mean)
        elif model.model_id == "seasonal_naive":
            raw = row.booked_passengers * model.route_conversion.get(row.route_id, model.global_conversion)
        else:
            vector = _vector(row, model.feature_names, model.category_levels)
            raw = model.coefficients.get("__intercept__", 0.0) + sum(
                model.coefficients.get(name, 0.0) * value for name, value in vector.items()
            )
        constrained = max(0.0, raw)
        predictions.append(
            Prediction(
                observation_id=row.observation_id,
                model_id=model.model_id,
                model_role=model.model_role,
                raw_prediction=raw,
                constrained_prediction=constrained,
                constraint_applied=abs(constrained - raw) > 0.0001,
            )
        )
    return predictions


def apply_capacity_constraints(
    predictions: list[Prediction], rows: list[ModelRow], allow_overbooking: bool
) -> list[Prediction]:
    """Apply explicit non-negative and capacity constraints."""
    constrained: list[Prediction] = []
    for prediction, row in zip(predictions, rows, strict=True):
        allowed_capacity = row.seat_capacity * (1.08 if allow_overbooking else 1.0)
        value = min(max(0.0, prediction.constrained_prediction), allowed_capacity)
        constrained.append(
            Prediction(
                observation_id=prediction.observation_id,
                model_id=prediction.model_id,
                model_role=prediction.model_role,
                raw_prediction=prediction.raw_prediction,
                constrained_prediction=round(value),
                constraint_applied=prediction.constraint_applied
                or abs(value - prediction.constrained_prediction) > 0.0001,
            )
        )
    return constrained


def _route_means(rows: list[ModelRow]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in rows:
        values.setdefault(row.route_id, []).append(row.target)
    return {route: sum(items) / len(items) for route, items in sorted(values.items())}


def _route_conversion(rows: list[ModelRow]) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    for row in rows:
        values.setdefault(row.route_id, []).append(row.target / max(1, row.booked_passengers))
    return {route: sum(items) / len(items) for route, items in sorted(values.items())}


def _feature_schema(rows: list[ModelRow]) -> tuple[list[str], dict[str, list[str]]]:
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


def _vector(row: ModelRow, feature_names: list[str], category_levels: dict[str, list[str]]) -> dict[str, float]:
    vector = {name: 0.0 for name in feature_names}
    for name, value in row.features.items():
        if isinstance(value, str):
            encoded = f"{name}={value}"
            if encoded in vector:
                vector[encoded] = 1.0
        elif name in vector:
            vector[name] = float(value)
    return vector


def _fit_linear_gradient_descent(
    rows: list[ModelRow],
    feature_names: list[str],
    category_levels: dict[str, list[str]],
    seed: int,
) -> dict[str, float]:
    coefficients = {name: 0.0 for name in feature_names}
    coefficients["__intercept__"] = sum(row.target for row in rows) / len(rows)
    learning_rate = 0.0000008 + seed * 0.0
    scale = {
        name: max(
            1.0, math.sqrt(sum(_vector(row, feature_names, category_levels)[name] ** 2 for row in rows) / len(rows))
        )
        for name in feature_names
    }
    for _ in range(700):
        gradients = {name: 0.0 for name in coefficients}
        for row in rows:
            vector = _vector(row, feature_names, category_levels)
            pred = coefficients["__intercept__"] + sum(
                coefficients[name] * (value / scale[name]) for name, value in vector.items()
            )
            error = pred - row.target
            gradients["__intercept__"] += error
            for name, value in vector.items():
                gradients[name] += error * (value / scale[name])
        for name in coefficients:
            coefficients[name] -= learning_rate * gradients[name] / len(rows)
    return {name: round(value / scale.get(name, 1.0), 10) for name, value in coefficients.items()}
