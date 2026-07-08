"""Drift-style comparison for monitoring metrics."""

from __future__ import annotations

from typing import Any

from airline_operations_intelligence.monitoring.config import MonitoringConfig
from airline_operations_intelligence.monitoring.contracts import DriftComparison, MonitoringMetric


def compare_drift(
    metrics: list[MonitoringMetric], baseline_manifest: dict[str, Any] | None, config: MonitoringConfig
) -> list[DriftComparison]:
    """Compare current metrics to a previous monitoring manifest."""
    threshold = float(config.settings.thresholds["drift_relative_change_warning"])
    critical = float(config.settings.thresholds["drift_relative_change_critical"])
    if baseline_manifest is None:
        return [
            DriftComparison(
                monitoring_domain="platform",
                metric_name="baseline_monitoring_run",
                current_value=None,
                baseline_value=None,
                absolute_change=None,
                relative_change=None,
                threshold=threshold,
                status="skipped",
                severity="info",
                notes="No baseline monitoring report directory supplied.",
            )
        ]
    baseline_metrics = {
        (row["monitoring_domain"], row["metric_name"]): float(row["metric_value"])
        for row in baseline_manifest.get("metric_values", [])
    }
    rows: list[DriftComparison] = []
    for metric in metrics:
        key = (metric.monitoring_domain, metric.metric_name)
        if key not in baseline_metrics:
            rows.append(_row(metric, None, None, None, threshold, "skipped", "info", "Metric absent from baseline."))
            continue
        baseline = baseline_metrics[key]
        absolute = metric.metric_value - baseline
        relative = _relative_change(metric.metric_value, baseline)
        status, severity = "passed", "info"
        if relative is not None and abs(relative) >= critical:
            status, severity = "failed", "critical"
        elif relative is not None and abs(relative) >= threshold:
            status, severity = "warning", "warning"
        rows.append(
            _row(
                metric,
                baseline,
                absolute,
                relative,
                threshold,
                status,
                severity,
                "Deterministic relative change comparison.",
            )
        )
    return sorted(rows, key=lambda row: (row.monitoring_domain, row.metric_name))


def _relative_change(current: float, baseline: float) -> float | None:
    if baseline == 0:
        return 0.0 if current == 0 else 1.0
    return (current - baseline) / abs(baseline)


def _row(
    metric: MonitoringMetric,
    baseline: float | None,
    absolute: float | None,
    relative: float | None,
    threshold: float,
    status: str,
    severity: str,
    notes: str,
) -> DriftComparison:
    return DriftComparison(
        monitoring_domain=metric.monitoring_domain,
        metric_name=metric.metric_name,
        current_value=metric.metric_value,
        baseline_value=baseline,
        absolute_change=absolute,
        relative_change=relative,
        threshold=threshold,
        status=status,
        severity=severity,
        notes=notes,
    )
