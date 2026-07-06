"""Writers for delay prediction artefacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.delay_prediction.contracts import DelayModel, DelayModelRow, DelayPrediction


def write_json(path: Path, payload: object) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_predictions(
    path: Path, delay_run_id: str, rows: list[DelayModelRow], predictions: list[DelayPrediction], partition: str
) -> str:
    """Write delay predictions CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "delay_run_id",
        "model_id",
        "model_role",
        "flight_id",
        "route_id",
        "origin_airport",
        "destination_airport",
        "operating_date",
        "scheduled_departure_utc",
        "prediction_cutoff_utc",
        "delay_probability",
        "predicted_delay_flag",
        "risk_band",
        "estimated_delay_minutes",
        "actual_delay_flag",
        "actual_delay_minutes",
        "weather_exposure_flag",
        "airport_event_exposure_flag",
        "partition",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row, prediction in zip(rows, predictions, strict=True):
            writer.writerow(
                {
                    "delay_run_id": delay_run_id,
                    "model_id": prediction.model_id,
                    "model_role": prediction.model_role,
                    "flight_id": row.flight_id,
                    "route_id": row.route_id,
                    "origin_airport": row.origin_airport,
                    "destination_airport": row.destination_airport,
                    "operating_date": row.operating_date.isoformat(),
                    "scheduled_departure_utc": row.scheduled_departure_utc.isoformat(),
                    "prediction_cutoff_utc": row.prediction_cutoff_utc.isoformat(),
                    "delay_probability": round(prediction.probability, 6),
                    "predicted_delay_flag": prediction.predicted_flag,
                    "risk_band": prediction.risk_band,
                    "estimated_delay_minutes": prediction.estimated_delay_minutes,
                    "actual_delay_flag": row.target,
                    "actual_delay_minutes": row.delay_minutes,
                    "weather_exposure_flag": row.weather_exposure_flag,
                    "airport_event_exposure_flag": row.airport_event_exposure_flag,
                    "partition": partition,
                }
            )
    return sha256_file(path)


def write_rows_csv(path: Path, rows: list[dict[str, object]]) -> str:
    """Write deterministic CSV rows and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def write_model_artefacts(
    model_dir: Path,
    champion: DelayModel,
    models: dict[str, DelayModel],
    metadata: dict[str, Any],
    candidate_rows: list[dict[str, object]],
    threshold_rows: list[dict[str, object]],
    calibration_rows: list[dict[str, object]],
) -> dict[str, str]:
    """Write local model artefacts and return checksums."""
    checksums = {
        "champion-model.json": write_json(model_dir / "champion-model.json", _model_payload(champion)),
        "model-metadata.json": write_json(model_dir / "model-metadata.json", metadata),
        "training-metrics.json": write_json(model_dir / "training-metrics.json", metadata["training_metrics"]),
        "validation-metrics.json": write_json(model_dir / "validation-metrics.json", metadata["validation_metrics"]),
        "test-metrics.json": write_json(model_dir / "test-metrics.json", metadata["test_metrics"]),
        "feature-schema.json": write_json(model_dir / "feature-schema.json", metadata["feature_schema"]),
        "feature-availability.json": write_json(
            model_dir / "feature-availability.json", metadata["feature_schema"]["feature_availability"]
        ),
        "leakage-checks.json": write_json(model_dir / "leakage-checks.json", metadata["leakage_checks"]),
        "environment.json": write_json(model_dir / "environment.json", metadata["environment"]),
        "secondary-regression-metadata.json": write_json(
            model_dir / "secondary-regression-metadata.json", metadata["secondary_regression_metadata"]
        ),
        "exclusion-summary.json": write_json(model_dir / "exclusion-summary.json", metadata["exclusion_summary"]),
        "candidate-comparison.csv": write_rows_csv(model_dir / "candidate-comparison.csv", candidate_rows),
        "threshold-comparison.csv": write_rows_csv(model_dir / "threshold-comparison.csv", threshold_rows),
        "calibration-bins.csv": write_rows_csv(model_dir / "calibration-bins.csv", calibration_rows),
        "calibration-metrics.csv": write_rows_csv(
            model_dir / "calibration-metrics.csv", metadata["calibration_metrics"]
        ),
    }
    importance = [
        {"feature_name": name, "importance": abs(value)}
        for name, value in sorted(champion.coefficients.items())
        if name != "__intercept__"
    ]
    checksums["feature-importance.csv"] = write_rows_csv(model_dir / "feature-importance.csv", importance)
    return checksums


def _model_payload(model: DelayModel) -> dict[str, object]:
    return {
        "model_id": model.model_id,
        "model_role": model.model_role,
        "parameters": model.parameters,
        "feature_names": model.feature_names,
        "category_levels": model.category_levels,
        "coefficients": model.coefficients,
        "route_rates": model.route_rates,
        "route_mean_delay": model.route_mean_delay,
        "global_rate": model.global_rate,
        "global_mean_delay": model.global_mean_delay,
    }
