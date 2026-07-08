"""Metric extraction for platform monitoring."""

from __future__ import annotations

from typing import Any

from airline_operations_intelligence.monitoring.contracts import MonitoringMetric, MonitoringSource


def extract_metrics(source: MonitoringSource) -> list[MonitoringMetric]:
    """Extract deterministic monitoring metrics from accepted manifests."""
    metrics: list[MonitoringMetric] = []
    if source.generation_manifest:
        metrics.extend(_generation_metrics(source.generation_manifest, source.generation_run_id))
    metrics.extend(_validation_metrics(source.validation_manifest, source.validation_run_id))
    for domain, manifest in sorted(source.optional_manifests.items()):
        if domain == "passenger_forecasting":
            metrics.extend(_forecast_metrics(manifest))
        elif domain == "delay_prediction":
            metrics.extend(_delay_metrics(manifest))
        elif domain == "maintenance_analytics":
            metrics.extend(_maintenance_metrics(manifest))
        elif domain == "disruption_scoring":
            metrics.extend(_disruption_metrics(manifest))
    return sorted(metrics, key=lambda metric: (metric.monitoring_domain, metric.metric_name))


def _metric(
    domain: str,
    name: str,
    value: float,
    run_id: str | None,
    *,
    numerator: float | None = None,
    denominator: float | None = None,
    threshold: float | None = None,
    notes: str = "",
) -> MonitoringMetric:
    return MonitoringMetric(
        domain, name, float(value), numerator, denominator, "observed", "info", threshold, run_id, "", notes
    )


def _generation_metrics(manifest: dict[str, Any], run_id: str | None) -> list[MonitoringMetric]:
    datasets = manifest.get("datasets", [])
    total_rows = sum(float(dataset.get("row_count", 0)) for dataset in datasets)
    return [
        _metric("generation", "generation_dataset_count", len(datasets), run_id),
        _metric("generation", "generation_total_rows", total_rows, run_id),
        _metric("generation", "generation_anomaly_count", _sum_map(manifest.get("anomaly_counts")), run_id),
        _metric("generation", "generation_cancellation_count", _sum_map(manifest.get("cancellation_counts")), run_id),
        _metric("generation", "generation_diversion_count", _sum_map(manifest.get("diversion_counts")), run_id),
        _metric("generation", "generation_manifest_complete_flag", 1.0, run_id),
        _metric("generation", "generation_checksum_verified_flag", 1.0, run_id),
    ]


def _validation_metrics(manifest: dict[str, Any], run_id: str) -> list[MonitoringMetric]:
    source_rows = float(manifest.get("source_row_count", 0))
    quarantined = float(manifest.get("quarantined_row_count", 0))
    invalid_rate = quarantined / source_rows if source_rows else 0.0
    return [
        _metric("validation", "validation_total_source_rows", source_rows, run_id),
        _metric("validation", "validation_total_valid_rows", manifest.get("valid_row_count", 0), run_id),
        _metric("validation", "validation_total_quarantined_rows", quarantined, run_id),
        _metric(
            "validation",
            "validation_invalid_record_rate",
            invalid_rate,
            run_id,
            numerator=quarantined,
            denominator=source_rows,
        ),
        _metric("validation", "validation_warning_count", manifest.get("warning_count", 0), run_id),
        _metric("validation", "validation_error_count", manifest.get("error_count", 0), run_id),
        _metric("validation", "validation_fatal_count", manifest.get("fatal_count", 0), run_id),
        _metric("validation", "validation_quality_metric_count", len(manifest.get("datasets", [])), run_id),
        _metric("validation", "validation_checksum_pass_flag", 1.0, run_id),
    ]


def _forecast_metrics(manifest: dict[str, Any]) -> list[MonitoringMetric]:
    run_id = str(manifest.get("forecast_run_id", ""))
    test = manifest.get("test_metrics", {})
    champion = manifest.get("champion_model", {})
    return [
        _metric("passenger_forecasting", "passenger_forecast_wape", test.get("wape", 0), run_id),
        _metric("passenger_forecasting", "passenger_forecast_mae", test.get("mae", 0), run_id),
        _metric("passenger_forecasting", "passenger_forecast_bias", test.get("bias", 0), run_id),
        _metric(
            "passenger_forecasting",
            "passenger_forecast_row_count",
            manifest.get("partition_row_counts", {}).get("test", 0),
            run_id,
        ),
        _metric("passenger_forecasting", "passenger_forecast_capacity_adjustment_count", 0, run_id),
        _metric(
            "passenger_forecasting",
            "passenger_forecast_champion_is_baseline_flag",
            1.0 if champion.get("model_role") == "baseline" else 0.0,
            run_id,
            notes=str(champion.get("model_id", "")),
        ),
    ]


def _delay_metrics(manifest: dict[str, Any]) -> list[MonitoringMetric]:
    run_id = str(manifest.get("delay_run_id", ""))
    test = manifest.get("test_metrics", {})
    return [
        _metric("delay_prediction", "delay_prediction_pr_auc", test.get("pr_auc", 0), run_id),
        _metric("delay_prediction", "delay_prediction_roc_auc", test.get("roc_auc", 0), run_id),
        _metric("delay_prediction", "delay_prediction_brier_score", test.get("brier_score", 0), run_id),
        _metric("delay_prediction", "delay_prediction_f1", test.get("f1", 0), run_id),
        _metric("delay_prediction", "delay_prediction_recall", test.get("recall", 0), run_id),
        _metric("delay_prediction", "delay_prediction_positive_rate", test.get("actual_positive_rate", 0), run_id),
        _metric("delay_prediction", "delay_prediction_high_risk_rate", 0, run_id),
    ]


def _maintenance_metrics(manifest: dict[str, Any]) -> list[MonitoringMetric]:
    run_id = str(manifest.get("maintenance_run_id", ""))
    rows = manifest.get("row_counts", {})
    risk = manifest.get("risk_band_counts", {})
    scores = float(rows.get("scores", 0))
    high = float(risk.get("high", 0) + risk.get("critical", 0))
    return [
        _metric("maintenance_analytics", "maintenance_observation_count", rows.get("scores", 0), run_id),
        _metric("maintenance_analytics", "maintenance_aircraft_count", manifest.get("aircraft_count", 0), run_id),
        _metric("maintenance_analytics", "maintenance_alert_count", rows.get("alerts", 0), run_id),
        _metric(
            "maintenance_analytics",
            "maintenance_high_risk_rate",
            high / scores if scores else 0,
            run_id,
            numerator=high,
            denominator=scores,
        ),
        _metric(
            "maintenance_analytics",
            "maintenance_max_risk_score",
            _max_component(manifest.get("component_score_summary")),
            run_id,
        ),
        _metric(
            "maintenance_analytics",
            "maintenance_human_review_count",
            1 if manifest.get("human_review_required") else 0,
            run_id,
        ),
    ]


def _disruption_metrics(manifest: dict[str, Any]) -> list[MonitoringMetric]:
    run_id = str(manifest.get("disruption_run_id", ""))
    rows = manifest.get("row_counts", {})
    risk = manifest.get("risk_band_counts", {})
    priority = manifest.get("recovery_priority_counts", {})
    scores = float(rows.get("scores", 0))
    severe = float(risk.get("severe", 0))
    high = float(risk.get("high", 0))
    component = manifest.get("component_score_summary", {})
    return [
        _metric("disruption_scoring", "disruption_score_row_count", rows.get("scores", 0), run_id),
        _metric("disruption_scoring", "disruption_alert_count", rows.get("alerts", 0), run_id),
        _metric(
            "disruption_scoring",
            "disruption_high_or_severe_rate",
            (high + severe) / scores if scores else 0,
            run_id,
            numerator=high + severe,
            denominator=scores,
        ),
        _metric(
            "disruption_scoring",
            "disruption_severe_rate",
            severe / scores if scores else 0,
            run_id,
            numerator=severe,
            denominator=scores,
        ),
        _metric("disruption_scoring", "disruption_urgent_review_count", priority.get("urgent_review", 0), run_id),
        _metric("disruption_scoring", "disruption_average_score", _average_component(component), run_id),
        _metric("disruption_scoring", "disruption_max_score", _max_component(component), run_id),
    ]


def _sum_map(raw: Any) -> float:
    return float(sum(value for value in raw.values())) if isinstance(raw, dict) else 0.0


def _max_component(raw: Any) -> float:
    if not isinstance(raw, dict):
        return 0.0
    return max((float(value.get("maximum", 0)) for value in raw.values() if isinstance(value, dict)), default=0.0)


def _average_component(raw: Any) -> float:
    if not isinstance(raw, dict) or not raw:
        return 0.0
    values = [float(value.get("average", 0)) for value in raw.values() if isinstance(value, dict)]
    return sum(values) / len(values) if values else 0.0
