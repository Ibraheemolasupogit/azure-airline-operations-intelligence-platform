"""Markdown reports and completed-run descriptions for monitoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import MonitoringArtefactError


def build_summary(manifest: dict[str, Any]) -> str:
    """Build monitoring summary markdown."""
    return "\n".join(
        [
            "# Monitoring Summary",
            "",
            f"- Monitoring run ID: `{manifest['monitoring_run_id']}`",
            f"- Source validation run: `{manifest['source_validation_run_id']}`",
            f"- Overall health status: `{manifest['overall_health_status']}`",
            f"- Highest severity: `{manifest['highest_severity']}`",
            f"- Monitored domains: {', '.join(manifest['monitored_domains'])}",
            f"- Alert count: {manifest['alert_counts']['total']}",
            f"- Drift status: {manifest['drift_policy']['status']}",
            "",
            "## Limitations",
            "",
            *[f"- {item}" for item in manifest["known_limitations"]],
            "",
            manifest["synthetic_data_declaration"],
            manifest["responsible_use_disclaimer"],
            "",
        ]
    )


def build_platform_health_report(manifest: dict[str, Any]) -> str:
    """Build platform health report markdown."""
    lines = [
        "# Platform Health Report",
        "",
        "## Domain Health",
        "",
    ]
    for row in manifest["domain_health"]:
        lines.append(
            f"- {row['monitoring_domain']}: {row['domain_status']} "
            f"(checks={row['check_count']}, alerts={row['alert_count']})"
        )
    lines.extend(
        [
            "",
            "## Warning And Failed Checks",
            "",
        ]
    )
    flagged = [row for row in manifest["check_summary"] if row["status"] in {"warning", "failed"}]
    lines.extend(
        [f"- {row['rule_id']} {row['monitoring_domain']}: {row['status']} {row['message']}" for row in flagged]
        or ["- No warning or failed checks."]
    )
    lines.extend(
        [
            "",
            "Recommended review action: Review monitoring evidence before any operational interpretation.",
            "",
        ]
    )
    return "\n".join(lines)


def build_governance_report(manifest: dict[str, Any]) -> str:
    """Build monitoring governance report markdown."""
    return "\n".join(
        [
            "# Monitoring Governance Report",
            "",
            "## Intended Use",
            "",
            "Local, deterministic monitoring evidence over synthetic portfolio artefacts.",
            "",
            "## Out Of Scope",
            "",
            "- Live Azure Monitor integration",
            "- Production incident management",
            "- Safety-critical or certified airline monitoring",
            "- Autonomous operational alerting",
            "",
            "## Severity Policy",
            "",
            *[f"- {key}: {value}" for key, value in manifest["monitoring_policy"]["severity_policy"].items()],
            "",
            "## Future Azure Mapping",
            "",
            "- Azure Monitor and Log Analytics: metrics, checks, and alerts",
            "- Application Insights: future application telemetry mapping only",
            "- Azure Data Explorer: operational telemetry summaries",
            "- Microsoft Purview: lineage",
            "- Power BI: dashboard-ready summaries in Milestone 10",
            "- Azure Machine Learning: model evidence metrics",
            "",
            manifest["responsible_use_disclaimer"],
            "",
        ]
    )


def describe_monitoring_report(monitoring_report_dir: Path) -> str:
    """Describe a completed monitoring run without rerunning checks."""
    manifest_path = monitoring_report_dir / "monitoring-manifest.json"
    if not manifest_path.exists():
        raise MonitoringArtefactError(f"Monitoring manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Monitoring run: {payload['monitoring_run_id']}",
            f"Source validation run: {payload['source_validation_run_id']}",
            f"Overall health status: {payload['overall_health_status']}",
            f"Highest severity: {payload['highest_severity']}",
            f"Monitored domains: {', '.join(payload['monitored_domains'])}",
            f"Checks: {payload['check_counts']}",
            f"Alerts: {payload['alert_counts']}",
            f"Status: {payload['overall_status']}",
        ]
    )
