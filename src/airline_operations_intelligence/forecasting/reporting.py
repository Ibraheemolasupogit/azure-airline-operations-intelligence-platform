"""Passenger forecasting reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import ForecastArtefactError


def build_summary(manifest: dict[str, Any]) -> str:
    """Build forecasting summary Markdown."""
    champion = manifest["champion_model"]
    return f"""# Passenger Forecasting Summary

## Run

- Forecast run ID: `{manifest["forecast_run_id"]}`
- Source validation run ID: `{manifest["source_validation_run_id"]}`
- Target: `{manifest["target_definition"]}`
- Prediction grain: `{manifest["prediction_grain"]}`
- Prediction horizon: `{manifest["prediction_horizon"]}` days
- Overall status: `{manifest["overall_status"]}`

## Partitions

- Train: {manifest["partition_row_counts"]["train"]} rows
- Validation: {manifest["partition_row_counts"]["validation"]} rows
- Test: {manifest["partition_row_counts"]["test"]} rows

## Champion

- Model: `{champion["model_id"]}`
- Rationale: {manifest["champion_selection_rationale"]}
- Validation WAPE: {manifest["validation_metrics"][champion["model_id"]]["wape"]:.6f}
- Test WAPE: {manifest["test_metrics"]["wape"]:.6f}

## Evidence

- Forecasts: `passenger_forecast.csv`
- Forecast metrics: `forecast-metrics.csv`
- Route summary: `route-forecast-summary.csv`
- Model artefacts: `{manifest["model_output_path"]}`
- Lineage: `lineage.json`

## Limitations

This is a deterministic local synthetic-data forecasting workflow. It is not a production
revenue-management, pricing, operations-control, or safety-critical model.
"""


def build_model_card(manifest: dict[str, Any]) -> str:
    """Build a model card from manifest evidence."""
    return f"""# Passenger Demand Model Card

## Intended Use

Forecast final synthetic passenger demand for scheduled flights at the configured booking horizon.

## Out Of Scope

This model is not for production revenue management, pricing, safety-critical operations, or
autonomous decision-making.

## Model

- Champion: `{manifest["champion_model"]["model_id"]}`
- Target: `{manifest["target_definition"]}`
- Features: {", ".join(manifest["feature_set"])}
- Split policy: chronological train, validation, and test partitions.
- Leakage controls: {", ".join(manifest["leakage_checks"])}
- Uncertainty: empirical validation residual intervals.
- Constraints: non-negative passenger forecasts and configured capacity tolerance.

## Azure ML Mapping

Future production mapping may use Azure Machine Learning data assets, command jobs, model registry
candidates, Azure Monitor metrics, and Microsoft Purview lineage. No Azure ML registration occurred.
"""


def build_evaluation_report(manifest: dict[str, Any]) -> str:
    """Build evaluation report from run metrics."""
    return f"""# Passenger Forecast Evaluation Report

## Metric Definitions

- MAE: mean absolute passenger error.
- RMSE: root mean squared passenger error.
- WAPE: sum absolute error divided by sum actual passengers.
- sMAPE: symmetric mean absolute percentage error.
- Bias: signed mean error.

## Champion Selection

{manifest["champion_selection_rationale"]}

## Final Test Metrics

```json
{json.dumps(manifest["test_metrics"], indent=2, sort_keys=True)}
```

## Capacity And Interval Evidence

- Constraint policy: {manifest["forecast_constraint_policy"]}
- Prediction interval method: {manifest["prediction_interval_method"]}
"""


def describe_forecast_report(report_dir: Path) -> str:
    """Describe a completed passenger forecast run without retraining."""
    manifest_path = report_dir / "forecast-manifest.json"
    if not manifest_path.exists():
        raise ForecastArtefactError(f"Forecast manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Forecast run ID: {manifest['forecast_run_id']}",
            f"Source validation run ID: {manifest['source_validation_run_id']}",
            f"Champion: {manifest['champion_model']['model_id']}",
            f"Overall status: {manifest['overall_status']}",
            f"Test WAPE: {manifest['test_metrics']['wape']:.6f}",
        ]
    )
