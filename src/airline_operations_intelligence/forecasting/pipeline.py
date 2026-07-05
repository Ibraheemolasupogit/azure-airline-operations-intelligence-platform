"""End-to-end passenger-demand forecasting pipeline."""

from __future__ import annotations

import csv
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import ForecastOutputCollisionError
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.forecasting.artefacts import (
    write_forecasts,
    write_json,
    write_metrics_csv,
    write_model_artefacts,
)
from airline_operations_intelligence.forecasting.config import (
    ForecastingConfig,
    build_forecast_run_id,
)
from airline_operations_intelligence.forecasting.contracts import (
    ForecastingSource,
    ForecastRunResult,
    ModelRow,
    PartitionedRows,
    Prediction,
    TrainedModel,
)
from airline_operations_intelligence.forecasting.discovery import discover_forecasting_source
from airline_operations_intelligence.forecasting.evaluation import evaluate_predictions, grouped_metrics
from airline_operations_intelligence.forecasting.features import (
    build_model_table,
    feature_availability_policy,
    feature_names,
)
from airline_operations_intelligence.forecasting.leakage import (
    assert_no_flight_crosses_partitions,
    assert_no_forbidden_features,
)
from airline_operations_intelligence.forecasting.lineage import build_lineage
from airline_operations_intelligence.forecasting.models import (
    apply_capacity_constraints,
    predict,
    train_model,
)
from airline_operations_intelligence.forecasting.prediction_intervals import interval_bounds, residual_quantiles
from airline_operations_intelligence.forecasting.reporting import (
    build_evaluation_report,
    build_model_card,
    build_summary,
)
from airline_operations_intelligence.forecasting.selection import select_champion
from airline_operations_intelligence.forecasting.splitting import chronological_split


def forecast_passenger_demand(
    *,
    validation_report_dir: Path,
    config: ForecastingConfig,
    forecast_run_id: str | None = None,
) -> ForecastRunResult:
    """Run local governed passenger-demand forecasting."""
    source = discover_forecasting_source(validation_report_dir, config)
    resolved_run_id = build_forecast_run_id(config, source.validation_run_id, forecast_run_id)
    final_output = config.settings.output_root / resolved_run_id
    final_model = config.settings.model_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_model = config.settings.model_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    finals = (final_output, final_model, final_report)
    tmps = (tmp_output, tmp_model, tmp_report)
    if any(path.exists() for path in finals) and not config.settings.overwrite:
        raise ForecastOutputCollisionError(f"Forecast run already exists: {resolved_run_id}. Use --overwrite.")
    for tmp in tmps:
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        for tmp in tmps:
            tmp.mkdir(parents=True, exist_ok=True)
        rows = build_model_table(source, config)
        leakage_checks = [*assert_no_forbidden_features(rows)]
        partitions = chronological_split(rows, config)
        leakage_checks.extend(assert_no_flight_crosses_partitions(partitions))
        models = {
            model_id: train_model(model_id, partitions.train, config) for model_id in config.settings.enabled_models
        }
        train_metrics = {}
        validation_metrics = {}
        validation_predictions = {}
        for model_id, model in models.items():
            train_predictions = apply_capacity_constraints(
                predict(model, partitions.train),
                partitions.train,
                config.settings.allow_controlled_overbooking,
            )
            val_predictions = apply_capacity_constraints(
                predict(model, partitions.validation),
                partitions.validation,
                config.settings.allow_controlled_overbooking,
            )
            train_metrics[model_id] = evaluate_predictions(partitions.train, train_predictions)
            validation_metrics[model_id] = evaluate_predictions(partitions.validation, val_predictions)
            validation_predictions[model_id] = val_predictions
        model_roles = {model_id: model.model_role for model_id, model in models.items()}
        champion_id, rationale = select_champion(validation_metrics, model_roles, config)
        champion = models[champion_id]
        champion_validation_predictions = validation_predictions[champion_id]
        test_predictions = apply_capacity_constraints(
            predict(champion, partitions.test),
            partitions.test,
            config.settings.allow_controlled_overbooking,
        )
        test_metrics = evaluate_predictions(partitions.test, test_predictions)
        interval_widths = residual_quantiles(
            partitions.validation,
            champion_validation_predictions,
            config.settings.prediction_interval_levels,
        )
        test_intervals = [
            interval_bounds(prediction.constrained_prediction, interval_widths) for prediction in test_predictions
        ]
        forecast_checksum = write_forecasts(
            tmp_output / "passenger_forecast.csv",
            resolved_run_id,
            partitions.test,
            test_predictions,
            test_intervals,
            "test",
        )
        metric_rows = _metric_rows(
            resolved_run_id, train_metrics, validation_metrics, test_metrics, partitions.test, test_predictions
        )
        metrics_checksum = write_metrics_csv(tmp_output / "forecast-metrics.csv", metric_rows)
        route_summary_checksum = write_metrics_csv(
            tmp_output / "route-forecast-summary.csv",
            grouped_metrics(partitions.test, test_predictions),
        )
        adjustment_checksum = _write_adjustments(
            tmp_output / "forecast-adjustments.csv", resolved_run_id, partitions.test, test_predictions
        )
        feature_schema: dict[str, Any] = {
            "feature_names": feature_names(rows),
            "feature_availability": feature_availability_policy(rows),
            "target": config.settings.target,
        }
        metadata = {
            "forecast_run_id": resolved_run_id,
            "source_validation_run_id": source.validation_run_id,
            "training_metrics": train_metrics,
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
            "feature_schema": feature_schema,
            "environment": {"package_version": __version__, "python": "3.11"},
            "partition_boundaries": partitions.boundaries,
            "seed": config.settings.seed,
            "known_limitations": [
                "Synthetic local forecasting only; no Azure ML registration occurred.",
                "Empirical intervals are based on small validation residual samples.",
            ],
        }
        model_checksums = write_model_artefacts(tmp_model, champion, models, metadata, interval_widths)
        completed = _utc_now()
        output_checksums = {
            "passenger_forecast.csv": forecast_checksum,
            "forecast-metrics.csv": metrics_checksum,
            "route-forecast-summary.csv": route_summary_checksum,
            "forecast-adjustments.csv": adjustment_checksum,
        }
        manifest = _manifest(
            resolved_run_id,
            source,
            config,
            started,
            completed,
            feature_schema,
            leakage_checks,
            partitions,
            models,
            champion_id,
            rationale,
            train_metrics,
            validation_metrics,
            test_metrics,
            interval_widths,
            output_checksums,
            model_checksums,
            final_output,
            final_model,
            final_report,
        )
        manifest_checksum = write_json(tmp_output / "forecast-manifest.json", manifest)
        lineage = build_lineage(
            forecast_run_id=resolved_run_id,
            source=source,
            output_dir=final_output,
            model_dir=final_model,
            report_dir=final_report,
            config_fingerprint=config.fingerprint(),
            champion_model_id=champion_id,
            timestamp_utc=completed,
        )
        lineage_checksum = write_json(tmp_report / "lineage.json", lineage)
        summary_checksum = _write_text(tmp_report / "forecasting-summary.md", build_summary(manifest))
        model_card_checksum = _write_text(tmp_report / "model-card.md", build_model_card(manifest))
        evaluation_checksum = _write_text(tmp_report / "evaluation-report.md", build_evaluation_report(manifest))
        output_artefacts = manifest["output_artefacts"]
        output_artefacts["forecast-manifest.json"] = manifest_checksum
        output_artefacts["lineage.json"] = lineage_checksum
        output_artefacts["forecasting-summary.md"] = summary_checksum
        output_artefacts["model-card.md"] = model_card_checksum
        output_artefacts["evaluation-report.md"] = evaluation_checksum
        write_json(tmp_report / "forecast-manifest.json", manifest)
        for final in finals:
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_model.replace(final_model)
        tmp_report.replace(final_report)
        return ForecastRunResult(
            forecast_run_id=resolved_run_id,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            model_dir=final_model,
            report_dir=final_report,
            manifest_path=final_report / "forecast-manifest.json",
            forecast_path=final_output / "passenger_forecast.csv",
            metrics_path=final_output / "forecast-metrics.csv",
            champion_model_id=champion_id,
            overall_status="passed",
            partition_row_counts={
                "train": len(partitions.train),
                "validation": len(partitions.validation),
                "test": len(partitions.test),
            },
        )
    except Exception:
        for tmp in tmps:
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _manifest(
    forecast_run_id: str,
    source: ForecastingSource,
    config: ForecastingConfig,
    started: str,
    completed: str,
    feature_schema: dict[str, Any],
    leakage_checks: list[str],
    partitions: PartitionedRows,
    models: dict[str, TrainedModel],
    champion_id: str,
    rationale: str,
    train_metrics: dict[str, dict[str, float]],
    validation_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, float],
    interval_widths: dict[str, float],
    output_checksums: dict[str, str],
    model_checksums: dict[str, str],
    final_output: Path,
    final_model: Path,
    final_report: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "forecast_run_id": forecast_run_id,
        "source_validation_run_id": source.validation_run_id,
        "source_validation_manifest_sha256": source.validation_manifest_sha256,
        "source_processed_checksums": source.processed_checksums,
        "forecasting_configuration": config.effective_configuration(),
        "forecasting_configuration_fingerprint": config.fingerprint(),
        "forecasting_package_version": __version__,
        "seed": config.settings.seed,
        "target_definition": config.settings.target,
        "prediction_grain": "one forecast per flight at configured booking horizon",
        "prediction_horizon": config.settings.prediction_horizon_days,
        "feature_set": feature_schema["feature_names"],
        "feature_availability_policy": feature_schema["feature_availability"],
        "leakage_checks": leakage_checks,
        "partition_boundaries": partitions.boundaries,
        "partition_row_counts": {
            "train": len(partitions.train),
            "validation": len(partitions.validation),
            "test": len(partitions.test),
        },
        "models_trained": sorted(models),
        "baselines_evaluated": sorted(model_id for model_id, model in models.items() if model.model_role == "baseline"),
        "champion_model": {"model_id": champion_id, "model_role": models[champion_id].model_role},
        "champion_selection_rationale": rationale,
        "training_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "prediction_interval_method": "empirical validation residual quantiles",
        "prediction_interval_widths": interval_widths,
        "forecast_constraint_policy": "non-negative integer forecasts capped at configured allowed capacity",
        "output_artefacts": {**output_checksums, **model_checksums},
        "forecast_output_path": final_output.as_posix(),
        "model_output_path": final_model.as_posix(),
        "report_output_path": final_report.as_posix(),
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed",
        "synthetic_data_declaration": "Forecasts are evaluation artefacts over fictional synthetic aviation data.",
        "known_limitations": [
            "Not a production revenue-management or safety-critical model.",
            "Small CI datasets use deterministic chronological row fallback.",
            "Azure ML mapping is documented only; no Azure resources are created.",
        ],
    }


def _metric_rows(
    forecast_run_id: str,
    train_metrics: dict[str, dict[str, float]],
    validation_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, float],
    test_rows: list[ModelRow],
    test_predictions: list[Prediction],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for partition, metrics_by_model in (("train", train_metrics), ("validation", validation_metrics)):
        for model_id, metrics in sorted(metrics_by_model.items()):
            for metric, value in sorted(metrics.items()):
                rows.append(
                    {
                        "forecast_run_id": forecast_run_id,
                        "partition": partition,
                        "model_id": model_id,
                        "dimension": "overall",
                        "value": "all",
                        "sample_size": "",
                        "metric": metric,
                        "metric_value": value,
                    }
                )
    for metric, value in sorted(test_metrics.items()):
        rows.append(
            {
                "forecast_run_id": forecast_run_id,
                "partition": "test",
                "model_id": "champion",
                "dimension": "overall",
                "value": "all",
                "sample_size": len(test_rows),
                "metric": metric,
                "metric_value": value,
            }
        )
    for group in grouped_metrics(test_rows, test_predictions):
        for metric_name, metric_value in sorted(group.items()):
            if metric_name not in {"dimension", "value", "sample_size"}:
                rows.append(
                    {
                        "forecast_run_id": forecast_run_id,
                        "partition": "test",
                        "model_id": "champion",
                        "dimension": group["dimension"],
                        "value": group["value"],
                        "sample_size": group["sample_size"],
                        "metric": metric_name,
                        "metric_value": metric_value,
                    }
                )
    return rows


def _write_adjustments(
    path: Path,
    forecast_run_id: str,
    rows: list[ModelRow],
    predictions: list[Prediction],
) -> str:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["forecast_run_id", "flight_id", "route_id", "raw_forecast", "forecast", "constraint_applied"],
        )
        writer.writeheader()
        for row, prediction in zip(rows, predictions, strict=True):
            writer.writerow(
                {
                    "forecast_run_id": forecast_run_id,
                    "flight_id": row.flight_id,
                    "route_id": row.route_id,
                    "raw_forecast": round(prediction.raw_prediction, 4),
                    "forecast": prediction.constrained_prediction,
                    "constraint_applied": prediction.constraint_applied,
                }
            )
    return sha256_file(path)


def _write_text(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
