"""Deterministic monitoring checks."""

from __future__ import annotations

from airline_operations_intelligence.monitoring.config import MonitoringConfig
from airline_operations_intelligence.monitoring.contracts import MonitoringCheck, MonitoringMetric, MonitoringSource


def run_monitoring_checks(
    source: MonitoringSource, metrics: list[MonitoringMetric], config: MonitoringConfig, timestamp_utc: str
) -> list[MonitoringCheck]:
    """Evaluate deterministic monitoring checks."""
    by_name = {metric.metric_name: metric for metric in metrics}
    checks: list[MonitoringCheck] = []
    if source.generation_manifest:
        checks.append(
            _present("MON-GEN-001", "generation", "generation_manifest_complete_flag", by_name, timestamp_utc)
        )
        checks.append(
            _equals_one("MON-GEN-002", "generation", "generation_checksum_verified_flag", by_name, timestamp_utc)
        )
    checks.extend(
        [
            _status("MON-VAL-001", "validation", "validation status accepted", "passed", timestamp_utc),
            _equals_one("MON-VAL-002", "validation", "validation_checksum_pass_flag", by_name, timestamp_utc),
            _max_threshold(
                "MON-VAL-003",
                "validation",
                "validation_invalid_record_rate",
                by_name,
                float(config.settings.thresholds["invalid_record_rate_warning"]),
                float(config.settings.thresholds["invalid_record_rate_critical"]),
                timestamp_utc,
            ),
            _max_threshold(
                "MON-VAL-004",
                "validation",
                "validation_error_count",
                by_name,
                float(config.settings.thresholds["validation_error_count_warning"]),
                float(config.settings.thresholds["validation_error_count_critical"]),
                timestamp_utc,
            ),
        ]
    )
    if "passenger_forecasting" in source.optional_manifests:
        checks.append(
            _present("MON-FCST-001", "passenger_forecasting", "passenger_forecast_wape", by_name, timestamp_utc)
        )
        checks.append(
            _max_threshold(
                "MON-FCST-002",
                "passenger_forecasting",
                "passenger_forecast_wape",
                by_name,
                float(config.settings.thresholds["passenger_forecast_wape_warning"]),
                float(config.settings.thresholds["passenger_forecast_wape_critical"]),
                timestamp_utc,
            )
        )
    if "delay_prediction" in source.optional_manifests:
        checks.append(_present("MON-DELAY-001", "delay_prediction", "delay_prediction_pr_auc", by_name, timestamp_utc))
        checks.append(
            _min_threshold(
                "MON-DELAY-002",
                "delay_prediction",
                "delay_prediction_pr_auc",
                by_name,
                float(config.settings.thresholds["delay_prediction_pr_auc_warning"]),
                float(config.settings.thresholds["delay_prediction_pr_auc_critical"]),
                timestamp_utc,
            )
        )
    if "maintenance_analytics" in source.optional_manifests:
        checks.append(
            _max_threshold(
                "MON-MAINT-001",
                "maintenance_analytics",
                "maintenance_high_risk_rate",
                by_name,
                float(config.settings.thresholds["maintenance_high_risk_rate_warning"]),
                1.0,
                timestamp_utc,
            )
        )
    if "disruption_scoring" in source.optional_manifests:
        checks.append(
            _present("MON-DISR-001", "disruption_scoring", "disruption_score_row_count", by_name, timestamp_utc)
        )
        checks.append(
            _max_threshold(
                "MON-DISR-002",
                "disruption_scoring",
                "disruption_severe_rate",
                by_name,
                float(config.settings.thresholds["disruption_severe_rate_warning"]),
                1.0,
                timestamp_utc,
            )
        )
    for accepted in source.accepted_inputs:
        if accepted.domain in {"baseline_monitoring"}:
            continue
        checks.append(
            _status(
                f"MON-LIN-{len(checks) + 1:03d}",
                accepted.domain,
                f"{accepted.domain} lineage and manifest accepted",
                "passed",
                timestamp_utc,
            )
        )
    return sorted(checks, key=lambda check: check.rule_id)


def _present(
    rule_id: str, domain: str, metric_name: str, metrics: dict[str, MonitoringMetric], timestamp_utc: str
) -> MonitoringCheck:
    metric = metrics.get(metric_name)
    if metric is None:
        return _check(
            rule_id, domain, "failed", "high", metric_name, None, "present", "Metric is missing.", timestamp_utc
        )
    return _check(
        rule_id,
        domain,
        "passed",
        "info",
        metric_name,
        metric.metric_value,
        "present",
        "Metric is present.",
        timestamp_utc,
    )


def _equals_one(
    rule_id: str, domain: str, metric_name: str, metrics: dict[str, MonitoringMetric], timestamp_utc: str
) -> MonitoringCheck:
    metric = metrics.get(metric_name)
    value = metric.metric_value if metric else 0.0
    status = "passed" if value == 1.0 else "failed"
    severity = "info" if status == "passed" else "critical"
    return _check(
        rule_id,
        domain,
        status,
        severity,
        metric_name,
        value,
        1.0,
        "Checksum verification flag evaluated.",
        timestamp_utc,
    )


def _max_threshold(
    rule_id: str,
    domain: str,
    metric_name: str,
    metrics: dict[str, MonitoringMetric],
    warning: float,
    critical: float,
    timestamp_utc: str,
) -> MonitoringCheck:
    metric = metrics.get(metric_name)
    value = metric.metric_value if metric else 0.0
    status = "passed"
    severity = "info"
    if value >= critical:
        status, severity = "failed", "critical"
    elif value >= warning:
        status, severity = "warning", "warning"
    return _check(
        rule_id, domain, status, severity, metric_name, value, warning, "Maximum threshold evaluated.", timestamp_utc
    )


def _min_threshold(
    rule_id: str,
    domain: str,
    metric_name: str,
    metrics: dict[str, MonitoringMetric],
    warning: float,
    critical: float,
    timestamp_utc: str,
) -> MonitoringCheck:
    metric = metrics.get(metric_name)
    value = metric.metric_value if metric else 0.0
    status = "passed"
    severity = "info"
    if value <= critical:
        status, severity = "failed", "critical"
    elif value <= warning:
        status, severity = "warning", "warning"
    return _check(
        rule_id, domain, status, severity, metric_name, value, warning, "Minimum threshold evaluated.", timestamp_utc
    )


def _status(rule_id: str, domain: str, message: str, status: str, timestamp_utc: str) -> MonitoringCheck:
    severity = "info" if status == "passed" else "high"
    return _check(rule_id, domain, status, severity, "status", status, "accepted", message, timestamp_utc)


def _check(
    rule_id: str,
    domain: str,
    status: str,
    severity: str,
    metric_name: str,
    observed: float | str | None,
    threshold: float | str | None,
    message: str,
    timestamp_utc: str,
) -> MonitoringCheck:
    return MonitoringCheck(
        rule_id=rule_id,
        monitoring_domain=domain,
        status=status,
        severity=severity,
        metric_name=metric_name,
        observed_value=observed,
        threshold=threshold,
        message=message,
        evidence_path="local monitoring evidence",
        remediation_hint="Review monitoring evidence.",
        timestamp_generated_utc=timestamp_utc,
    )
