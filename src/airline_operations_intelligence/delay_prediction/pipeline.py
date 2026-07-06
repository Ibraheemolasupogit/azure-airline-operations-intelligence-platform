"""End-to-end flight-delay prediction pipeline."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import DelayOutputCollisionError
from airline_operations_intelligence.delay_prediction.artefacts import (
    write_json,
    write_model_artefacts,
    write_predictions,
    write_rows_csv,
)
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig, build_delay_run_id
from airline_operations_intelligence.delay_prediction.contracts import (
    DelayModel,
    DelayModelRow,
    DelayPrediction,
    DelayRunResult,
    PartitionedDelayRows,
)
from airline_operations_intelligence.delay_prediction.discovery import discover_delay_prediction_source
from airline_operations_intelligence.delay_prediction.evaluation import (
    calibration_bins,
    evaluate_probabilities,
    grouped_metrics,
    threshold_rows,
)
from airline_operations_intelligence.delay_prediction.features import (
    build_model_table,
    feature_availability_policy,
    feature_names,
)
from airline_operations_intelligence.delay_prediction.leakage import (
    assert_no_flight_crosses_partitions,
    assert_no_forbidden_features,
)
from airline_operations_intelligence.delay_prediction.lineage import build_lineage
from airline_operations_intelligence.delay_prediction.models import (
    estimate_delay_minutes,
    predict_probability,
    train_model,
)
from airline_operations_intelligence.delay_prediction.reporting import (
    build_evaluation_report,
    build_feature_availability_report,
    build_model_card,
    build_summary,
)
from airline_operations_intelligence.delay_prediction.selection import select_champion, select_threshold


def predict_flight_delays(
    *,
    validation_report_dir: Path,
    config: DelayPredictionConfig,
    passenger_forecast_report_dir: Path | None = None,
    delay_run_id: str | None = None,
) -> DelayRunResult:
    """Run local governed flight-delay prediction."""
    source = discover_delay_prediction_source(validation_report_dir, config, passenger_forecast_report_dir)
    resolved_run_id = build_delay_run_id(
        config,
        source.validation_run_id,
        source.passenger_forecast.forecast_run_id if source.passenger_forecast else None,
        delay_run_id,
    )
    final_output = config.settings.output_root / resolved_run_id
    final_model = config.settings.model_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_model = config.settings.model_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    finals = (final_output, final_model, final_report)
    tmps = (tmp_output, tmp_model, tmp_report)
    if any(path.exists() for path in finals) and not config.settings.overwrite:
        raise DelayOutputCollisionError(f"Delay prediction run already exists: {resolved_run_id}. Use --overwrite.")
    for tmp in tmps:
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        for tmp in tmps:
            tmp.mkdir(parents=True, exist_ok=True)
        rows, exclusions = build_model_table(source, config)
        leakage_checks = [*assert_no_forbidden_features(rows)]
        partitions = chronological_delay_split(rows, config)
        leakage_checks.extend(assert_no_flight_crosses_partitions(partitions))
        models = {
            model_id: train_model(model_id, partitions.train, config) for model_id in config.settings.enabled_models
        }
        train_metrics: dict[str, dict[str, float]] = {}
        validation_metrics: dict[str, dict[str, float]] = {}
        validation_probabilities: dict[str, list[float]] = {}
        for model_id, model in models.items():
            train_probabilities = predict_probability(model, partitions.train)
            val_probabilities = predict_probability(model, partitions.validation)
            train_metrics[model_id] = evaluate_probabilities(
                partitions.train,
                train_probabilities,
                config.settings.default_probability_threshold,
            )
            validation_metrics[model_id] = evaluate_probabilities(
                partitions.validation,
                val_probabilities,
                config.settings.default_probability_threshold,
            )
            validation_probabilities[model_id] = val_probabilities
        model_roles = {model_id: model.model_role for model_id, model in models.items()}
        champion_id, champion_rationale = select_champion(validation_metrics, model_roles, config)
        champion = models[champion_id]
        threshold_metrics = threshold_rows(partitions.validation, validation_probabilities[champion_id], config)
        selected_threshold, threshold_rationale = select_threshold(threshold_metrics, config)
        test_probabilities = predict_probability(champion, partitions.test)
        test_estimates = estimate_delay_minutes(champion, partitions.test, test_probabilities)
        test_predictions = _predictions(
            champion, partitions.test, test_probabilities, test_estimates, selected_threshold, config
        )
        test_metrics = evaluate_probabilities(partitions.test, test_probabilities, selected_threshold)
        completed = _utc_now()
        prediction_checksum = write_predictions(
            tmp_output / "delay_predictions.csv",
            resolved_run_id,
            partitions.test,
            test_predictions,
            "test",
        )
        metrics_rows = _metric_rows(train_metrics, validation_metrics, test_metrics)
        metrics_checksum = write_rows_csv(tmp_output / "delay-metrics.csv", metrics_rows)
        grouped_checksum = write_rows_csv(
            tmp_output / "grouped-delay-metrics.csv",
            grouped_metrics(partitions.test, test_probabilities, selected_threshold),
        )
        risk_checksum = write_rows_csv(tmp_output / "risk-band-summary.csv", _risk_band_summary(test_predictions))
        adjustments_checksum = write_rows_csv(
            tmp_output / "prediction-adjustments.csv",
            _prediction_adjustments(resolved_run_id, partitions.test, test_predictions),
        )
        feature_schema = {
            "feature_names": feature_names(rows),
            "feature_availability": feature_availability_policy(rows),
            "target": config.settings.target,
        }
        candidate_rows = _candidate_rows(validation_metrics, models)
        calibration = calibration_bins(partitions.test, test_probabilities, config.settings.probability_bins)
        metadata = _metadata(
            resolved_run_id,
            source,
            config,
            train_metrics,
            validation_metrics,
            test_metrics,
            feature_schema,
            leakage_checks,
            partitions,
            exclusions,
            selected_threshold,
        )
        model_checksums = write_model_artefacts(
            tmp_model,
            champion,
            models,
            metadata,
            candidate_rows,
            threshold_metrics,
            calibration,
        )
        output_checksums = {
            "delay_predictions.csv": prediction_checksum,
            "delay-metrics.csv": metrics_checksum,
            "grouped-delay-metrics.csv": grouped_checksum,
            "risk-band-summary.csv": risk_checksum,
            "prediction-adjustments.csv": adjustments_checksum,
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
            champion_id,
            champion_rationale,
            selected_threshold,
            threshold_rationale,
            train_metrics,
            validation_metrics,
            test_metrics,
            exclusions,
            output_checksums,
            model_checksums,
            final_output,
            final_model,
            final_report,
        )
        manifest_checksum = write_json(tmp_output / "delay-prediction-manifest.json", manifest)
        lineage_checksum = write_json(
            tmp_report / "lineage.json",
            build_lineage(
                delay_run_id=resolved_run_id,
                source=source,
                output_dir=final_output,
                model_dir=final_model,
                report_dir=final_report,
                config_fingerprint=config.fingerprint(),
                champion_model_id=champion_id,
                timestamp_utc=completed,
            ),
        )
        summary_checksum = _write_text(tmp_report / "delay-prediction-summary.md", build_summary(manifest))
        model_card_checksum = _write_text(tmp_report / "model-card.md", build_model_card(manifest))
        evaluation_checksum = _write_text(tmp_report / "evaluation-report.md", build_evaluation_report(manifest))
        feature_report_checksum = _write_text(
            tmp_report / "feature-availability-report.md",
            build_feature_availability_report(manifest),
        )
        manifest["output_artefacts"]["delay-prediction-manifest.json"] = manifest_checksum
        manifest["output_artefacts"]["lineage.json"] = lineage_checksum
        manifest["output_artefacts"]["delay-prediction-summary.md"] = summary_checksum
        manifest["output_artefacts"]["model-card.md"] = model_card_checksum
        manifest["output_artefacts"]["evaluation-report.md"] = evaluation_checksum
        manifest["output_artefacts"]["feature-availability-report.md"] = feature_report_checksum
        write_json(tmp_report / "delay-prediction-manifest.json", manifest)
        for final in finals:
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_model.replace(final_model)
        tmp_report.replace(final_report)
        return DelayRunResult(
            delay_run_id=resolved_run_id,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            model_dir=final_model,
            report_dir=final_report,
            manifest_path=final_report / "delay-prediction-manifest.json",
            predictions_path=final_output / "delay_predictions.csv",
            metrics_path=final_output / "delay-metrics.csv",
            champion_model_id=champion_id,
            selected_threshold=selected_threshold,
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


def chronological_delay_split(rows: list[DelayModelRow], config: DelayPredictionConfig) -> PartitionedDelayRows:
    """Import wrapper kept small to make orchestration easier to read."""
    from airline_operations_intelligence.delay_prediction.splitting import chronological_split

    return chronological_split(rows, config)


def _predictions(
    model: DelayModel,
    rows: list[DelayModelRow],
    probabilities: list[float],
    estimates: list[float],
    threshold: float,
    config: DelayPredictionConfig,
) -> list[DelayPrediction]:
    predictions: list[DelayPrediction] = []
    for row, probability, estimate in zip(rows, probabilities, estimates, strict=True):
        predictions.append(
            DelayPrediction(
                observation_id=row.observation_id,
                model_id=model.model_id,
                model_role=model.model_role,
                probability=probability,
                predicted_flag=1 if probability >= threshold else 0,
                risk_band=_risk_band(probability, config),
                estimated_delay_minutes=estimate,
            )
        )
    return predictions


def _risk_band(probability: float, config: DelayPredictionConfig) -> str:
    for band in config.settings.risk_bands:
        if band.minimum_probability <= probability <= band.maximum_probability:
            return band.name
    return config.settings.risk_bands[-1].name


def _metric_rows(
    train: dict[str, dict[str, float]],
    validation: dict[str, dict[str, float]],
    test: dict[str, float],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for partition, payload in (("train", train), ("validation", validation)):
        for model_id, metrics in sorted(payload.items()):
            rows.extend(
                {"partition": partition, "model_id": model_id, "metric": key, "value": value}
                for key, value in sorted(metrics.items())
            )
    rows.extend(
        {"partition": "test", "model_id": "champion", "metric": key, "value": value}
        for key, value in sorted(test.items())
    )
    return rows


def _candidate_rows(metrics: dict[str, dict[str, float]], models: dict[str, DelayModel]) -> list[dict[str, object]]:
    return [
        {
            "model_id": model_id,
            "model_role": models[model_id].model_role,
            "validation_pr_auc": values["pr_auc"],
            "validation_roc_auc": values["roc_auc"],
            "validation_f1": values["f1"],
            "validation_brier_score": values["brier_score"],
        }
        for model_id, values in sorted(metrics.items())
    ]


def _risk_band_summary(predictions: list[DelayPrediction]) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for prediction in predictions:
        counts[prediction.risk_band] = counts.get(prediction.risk_band, 0) + 1
    return [{"risk_band": band, "prediction_count": count} for band, count in sorted(counts.items())]


def _prediction_adjustments(
    delay_run_id: str, rows: list[DelayModelRow], predictions: list[DelayPrediction]
) -> list[dict[str, object]]:
    return [
        {
            "delay_run_id": delay_run_id,
            "flight_id": row.flight_id,
            "recommended_review": prediction.risk_band == "high",
            "suggested_action": "review_turnaround_and_crew_buffer" if prediction.risk_band == "high" else "monitor",
        }
        for row, prediction in zip(rows, predictions, strict=True)
    ]


def _metadata(
    delay_run_id: str,
    source: Any,
    config: DelayPredictionConfig,
    train_metrics: dict[str, dict[str, float]],
    validation_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, float],
    feature_schema: dict[str, Any],
    leakage_checks: list[str],
    partitions: PartitionedDelayRows,
    exclusions: dict[str, int],
    selected_threshold: float,
) -> dict[str, Any]:
    return {
        "delay_run_id": delay_run_id,
        "source_validation_run_id": source.validation_run_id,
        "optional_passenger_forecast_run_id": source.passenger_forecast.forecast_run_id
        if source.passenger_forecast
        else None,
        "training_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "feature_schema": feature_schema,
        "leakage_checks": leakage_checks,
        "environment": {"package_version": __version__, "python": "3.11"},
        "partition_boundaries": partitions.boundaries,
        "seed": config.settings.seed,
        "selected_probability_threshold": selected_threshold,
        "secondary_regression_metadata": {
            "enabled": config.settings.enable_secondary_delay_regression,
            "method": "route mean delay from training rows scaled by predicted probability",
            "non_negative_constraint": True,
        },
        "exclusion_summary": exclusions,
        "calibration_metrics": [{"metric": "brier_score", "value": test_metrics["brier_score"]}],
    }


def _manifest(
    delay_run_id: str,
    source: Any,
    config: DelayPredictionConfig,
    started: str,
    completed: str,
    feature_schema: dict[str, Any],
    leakage_checks: list[str],
    partitions: PartitionedDelayRows,
    champion_id: str,
    champion_rationale: str,
    selected_threshold: float,
    threshold_rationale: str,
    train_metrics: dict[str, dict[str, float]],
    validation_metrics: dict[str, dict[str, float]],
    test_metrics: dict[str, float],
    exclusions: dict[str, int],
    output_checksums: dict[str, str],
    model_checksums: dict[str, str],
    output_dir: Path,
    model_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "delay_run_id": delay_run_id,
        "source_validation_run_id": source.validation_run_id,
        "source_validation_manifest_sha256": source.validation_manifest_sha256,
        "optional_passenger_forecast_run_id": source.passenger_forecast.forecast_run_id
        if source.passenger_forecast
        else None,
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed",
        "target": {
            "name": config.settings.target,
            "delay_threshold_minutes": config.settings.delay_threshold_minutes,
            "prediction_cutoff_minutes": config.settings.prediction_cutoff_minutes,
            "prediction_grain": "scheduled_flight",
        },
        "configuration_fingerprint": config.fingerprint(),
        "feature_schema": feature_schema,
        "leakage_checks": leakage_checks,
        "partition_boundaries": partitions.boundaries,
        "partition_row_counts": {
            "train": len(partitions.train),
            "validation": len(partitions.validation),
            "test": len(partitions.test),
        },
        "class_distribution": {
            "train_positive": sum(row.target for row in partitions.train),
            "validation_positive": sum(row.target for row in partitions.validation),
            "test_positive": sum(row.target for row in partitions.test),
        },
        "champion_model_id": champion_id,
        "champion_rationale": champion_rationale,
        "selected_probability_threshold": selected_threshold,
        "threshold_rationale": threshold_rationale,
        "training_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "exclusion_summary": exclusions,
        "input_checksums": source.processed_checksums,
        "output_artefacts": {**output_checksums, **model_checksums},
        "output_dirs": {
            "predictions": output_dir.as_posix(),
            "models": model_dir.as_posix(),
            "reports": report_dir.as_posix(),
        },
        "known_limitations": [
            "Synthetic local classifier only; no Azure ML registration occurred.",
            "Small CI datasets can produce unstable validation metrics.",
            "Secondary delay minutes are a simple non-negative training-history estimate.",
        ],
        "milestone_scope": (
            "Milestone 5 flight-delay prediction only; no Milestone 6 or later functionality is implemented."
        ),
    }


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    from airline_operations_intelligence.data_generation.writers import sha256_file

    return sha256_file(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
