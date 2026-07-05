"""Writers for passenger forecasting artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.forecasting.contracts import ModelRow, Prediction, TrainedModel


def write_json(path: Path, payload: object) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_model_artefacts(
    model_dir: Path,
    champion: TrainedModel,
    models: dict[str, TrainedModel],
    metadata: dict[str, Any],
    residuals: dict[str, float],
) -> dict[str, str]:
    """Write local model artefacts and return checksums."""
    checksums = {
        "champion-model.json": write_json(model_dir / "champion-model.json", _model_payload(champion)),
        "model-metadata.json": write_json(model_dir / "model-metadata.json", metadata),
        "training-metrics.json": write_json(model_dir / "training-metrics.json", metadata["training_metrics"]),
        "validation-metrics.json": write_json(model_dir / "validation-metrics.json", metadata["validation_metrics"]),
        "test-metrics.json": write_json(model_dir / "test-metrics.json", metadata["test_metrics"]),
        "residual-distribution.json": write_json(model_dir / "residual-distribution.json", residuals),
        "prediction-interval-metadata.json": write_json(
            model_dir / "prediction-interval-metadata.json",
            {"method": "empirical validation residual quantiles", "quantiles": residuals},
        ),
        "environment.json": write_json(model_dir / "environment.json", metadata["environment"]),
        "feature-schema.json": write_json(model_dir / "feature-schema.json", metadata["feature_schema"]),
    }
    with (model_dir / "candidate-comparison.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["model_id", "model_role", "validation_wape", "validation_mae"])
        writer.writeheader()
        for model_id, model in sorted(models.items()):
            metrics = metadata["validation_metrics"][model_id]
            writer.writerow(
                {
                    "model_id": model_id,
                    "model_role": model.model_role,
                    "validation_wape": metrics["wape"],
                    "validation_mae": metrics["mae"],
                }
            )
    checksums["candidate-comparison.csv"] = sha256_file(model_dir / "candidate-comparison.csv")
    with (model_dir / "feature-importance.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["feature_name", "importance"])
        writer.writeheader()
        for name, value in sorted(champion.coefficients.items()):
            if name != "__intercept__":
                writer.writerow({"feature_name": name, "importance": abs(value)})
    checksums["feature-importance.csv"] = sha256_file(model_dir / "feature-importance.csv")
    return checksums


def write_forecasts(
    path: Path,
    forecast_run_id: str,
    rows: list[ModelRow],
    predictions: list[Prediction],
    intervals: list[dict[str, float]],
    partition: str,
) -> str:
    """Write passenger forecast CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "forecast_run_id",
        "model_id",
        "model_role",
        "flight_id",
        "route_id",
        "operating_date",
        "observation_date",
        "prediction_horizon_days",
        "actual_passengers",
        "raw_forecast_passengers",
        "forecast_passengers",
        "forecast_lower_80",
        "forecast_upper_80",
        "forecast_lower_95",
        "forecast_upper_95",
        "seat_capacity",
        "allowed_capacity",
        "constraint_applied",
        "absolute_error",
        "signed_error",
        "percentage_error",
        "partition",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row, prediction, interval in zip(rows, predictions, intervals, strict=True):
            signed = prediction.constrained_prediction - row.target
            writer.writerow(
                {
                    "forecast_run_id": forecast_run_id,
                    "model_id": prediction.model_id,
                    "model_role": prediction.model_role,
                    "flight_id": row.flight_id,
                    "route_id": row.route_id,
                    "operating_date": row.operating_date.isoformat(),
                    "observation_date": row.observation_date.isoformat(),
                    "prediction_horizon_days": row.days_before_departure,
                    "actual_passengers": row.target,
                    "raw_forecast_passengers": round(prediction.raw_prediction, 4),
                    "forecast_passengers": prediction.constrained_prediction,
                    "forecast_lower_80": interval.get("lower_80", ""),
                    "forecast_upper_80": interval.get("upper_80", ""),
                    "forecast_lower_95": interval.get("lower_95", ""),
                    "forecast_upper_95": interval.get("upper_95", ""),
                    "seat_capacity": row.seat_capacity,
                    "allowed_capacity": round(row.seat_capacity * 1.08),
                    "constraint_applied": prediction.constraint_applied,
                    "absolute_error": abs(signed),
                    "signed_error": signed,
                    "percentage_error": "" if row.target == 0 else abs(signed) / row.target,
                    "partition": partition,
                }
            )
    return sha256_file(path)


def write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> str:
    """Write forecast metrics CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def _model_payload(model: TrainedModel) -> dict[str, object]:
    return {
        "model_id": model.model_id,
        "model_role": model.model_role,
        "parameters": model.parameters,
        "feature_names": model.feature_names,
        "category_levels": model.category_levels,
        "coefficients": model.coefficients,
        "route_means": model.route_means,
        "global_mean": model.global_mean,
        "route_conversion": model.route_conversion,
        "global_conversion": model.global_conversion,
    }
