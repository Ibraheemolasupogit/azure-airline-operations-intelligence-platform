"""Monitoring alert generation."""

from __future__ import annotations

import hashlib

from airline_operations_intelligence.monitoring.config import MonitoringConfig
from airline_operations_intelligence.monitoring.contracts import MonitoringAlert, MonitoringCheck


def generate_monitoring_alerts(
    monitoring_run_id: str, checks: list[MonitoringCheck], config: MonitoringConfig
) -> list[MonitoringAlert]:
    """Generate deterministic alerts from warning and failed checks."""
    order = config.settings.severity_policy
    selected = [check for check in checks if check.status in {"warning", "failed"}]
    selected.sort(key=lambda check: (-order[check.severity], check.rule_id))
    alerts = [
        MonitoringAlert(
            monitoring_alert_id=_alert_id(monitoring_run_id, check),
            monitoring_run_id=monitoring_run_id,
            rule_id=check.rule_id,
            monitoring_domain=check.monitoring_domain,
            severity=check.severity,
            status=check.status,
            alert_title=f"{check.rule_id} {check.monitoring_domain} monitoring check {check.status}",
            alert_message=check.message,
            observed_value=check.observed_value,
            threshold=check.threshold,
            evidence_path=check.evidence_path,
            recommended_review_action=_action(check.monitoring_domain),
            human_review_required=True,
            synthetic_data_warning="Local synthetic monitoring evidence only; do not trigger operational action.",
        )
        for check in selected[: config.settings.maximum_alerts_per_run]
    ]
    return alerts


def _alert_id(run_id: str, check: MonitoringCheck) -> str:
    payload = f"{run_id}|{check.rule_id}|{check.monitoring_domain}|{check.metric_name}"
    return "MON-ALERT-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _action(domain: str) -> str:
    actions = {
        "validation": "Review validation quality metrics.",
        "passenger_forecasting": "Review model evidence before operational interpretation.",
        "delay_prediction": "Review model evidence before operational interpretation.",
        "generation": "Inspect source manifest and checksums.",
    }
    return actions.get(domain, "Review monitoring evidence.")
