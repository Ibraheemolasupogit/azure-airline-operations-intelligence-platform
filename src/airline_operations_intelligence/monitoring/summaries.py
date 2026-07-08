"""Monitoring domain and platform summary aggregation."""

from __future__ import annotations

from collections import Counter

from airline_operations_intelligence.monitoring.contracts import (
    DOMAINS,
    MonitoringAlert,
    MonitoringCheck,
    MonitoringMetric,
)


def domain_health_summary(
    monitoring_run_id: str,
    metrics: list[MonitoringMetric],
    checks: list[MonitoringCheck],
    alerts: list[MonitoringAlert],
    source_run_ids: dict[str, str | None],
    source_manifest_paths: dict[str, str | None],
) -> list[dict[str, object]]:
    """Build one summary row per supported domain."""
    rows: list[dict[str, object]] = []
    for domain in DOMAINS:
        domain_metrics = [metric for metric in metrics if metric.monitoring_domain == domain]
        domain_checks = [check for check in checks if check.monitoring_domain == domain]
        domain_alerts = [alert for alert in alerts if alert.monitoring_domain == domain]
        counts = Counter(check.status for check in domain_checks)
        highest = _highest([check.severity for check in domain_checks] + [alert.severity for alert in domain_alerts])
        rows.append(
            {
                "monitoring_run_id": monitoring_run_id,
                "monitoring_domain": domain,
                "domain_status": _status(counts),
                "highest_severity": highest,
                "metric_count": len(domain_metrics),
                "check_count": len(domain_checks),
                "passed_check_count": counts["passed"],
                "warning_check_count": counts["warning"],
                "failed_check_count": counts["failed"],
                "skipped_check_count": counts["skipped"],
                "alert_count": len(domain_alerts),
                "source_run_id": source_run_ids.get(domain),
                "source_manifest_path": source_manifest_paths.get(domain),
            }
        )
    return rows


def platform_health_summary(
    monitoring_run_id: str,
    domain_rows: list[dict[str, object]],
    checks: list[MonitoringCheck],
    alerts: list[MonitoringAlert],
    timestamp: str,
) -> list[dict[str, object]]:
    """Build a single platform health summary row."""
    counts = Counter(check.status for check in checks)
    alert_counts = Counter(alert.severity for alert in alerts)
    highest = _highest([str(row["highest_severity"]) for row in domain_rows] + [alert.severity for alert in alerts])
    return [
        {
            "monitoring_run_id": monitoring_run_id,
            "overall_health_status": _status(counts),
            "highest_severity": highest,
            "domain_count": len(domain_rows),
            "monitored_domain_count": sum(1 for row in domain_rows if _int_value(row["metric_count"]) > 0),
            "passed_check_count": counts["passed"],
            "warning_check_count": counts["warning"],
            "failed_check_count": counts["failed"],
            "skipped_check_count": counts["skipped"],
            "alert_count": len(alerts),
            "critical_alert_count": alert_counts["critical"],
            "high_alert_count": alert_counts["high"],
            "generated_at_utc": timestamp,
        }
    ]


def _status(counts: Counter[str]) -> str:
    if counts["failed"]:
        return "failed"
    if counts["warning"]:
        return "warning"
    return "passed"


def _highest(severities: list[str]) -> str:
    order = {"info": 0, "warning": 1, "high": 2, "critical": 3}
    return max(severities or ["info"], key=lambda severity: order.get(severity, 0))


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value))
