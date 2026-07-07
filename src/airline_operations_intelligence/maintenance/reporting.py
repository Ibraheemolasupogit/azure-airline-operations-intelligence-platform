"""Maintenance analytics reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import MaintenanceArtefactError


def build_summary(manifest: dict[str, Any]) -> str:
    """Build maintenance analytics summary."""
    return "\n".join(
        [
            "# Maintenance Analytics Summary",
            "",
            f"- Run ID: `{manifest['maintenance_run_id']}`",
            f"- Source validation run: `{manifest['source_validation_run_id']}`",
            f"- Aircraft count: `{manifest['aircraft_count']}`",
            f"- Telemetry observations: `{manifest['row_counts']['features']}`",
            f"- Linked flights: `{manifest['linked_flight_count']}`",
            f"- Risk bands: `{manifest['risk_band_counts']}`",
            f"- Alerts: `{manifest['alert_counts']}`",
            "",
            "Rules-based synthetic analytics only; human review is required for any real-world interpretation.",
            "",
        ]
    )


def build_aircraft_health_report(manifest: dict[str, Any]) -> str:
    """Build aircraft health report."""
    return "\n".join(
        [
            "# Aircraft Health Report",
            "",
            f"- Aircraft analysed: `{manifest['aircraft_count']}`",
            f"- Highest-risk aircraft: `{manifest['highest_risk_aircraft']}`",
            f"- Component score summary: `{manifest['component_score_summary']}`",
            "",
            "Sensor breaches, anomaly scores, degradation trends, utilisation, fault-code evidence, and retrospective",
            "operational context are decision-support signals only.",
            "",
        ]
    )


def build_governance_report(manifest: dict[str, Any]) -> str:
    """Build governance report."""
    return "\n".join(
        [
            "# Maintenance Analytics Governance",
            "",
            "## Intended Use",
            "Synthetic portfolio analytics for aircraft-health evidence exploration.",
            "",
            "## Out Of Scope",
            "Certified predictive maintenance, airworthiness evidence, maintenance-control decisions,",
            "dispatch decisions,",
            "or safety-critical diagnostics.",
            "",
            f"- Configuration fingerprint: `{manifest['configuration_fingerprint']}`",
            f"- Human review required: `{manifest['human_review_required']}`",
            f"- Synthetic-data declaration: {manifest['synthetic_data_declaration']}",
            "",
        ]
    )


def describe_aircraft_health_report(report_dir: Path) -> str:
    """Describe a completed maintenance analytics run."""
    manifest_path = report_dir / "maintenance-analytics-manifest.json"
    if not manifest_path.is_file():
        raise MaintenanceArtefactError(f"Maintenance analytics manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Maintenance analytics run: {manifest['maintenance_run_id']}",
            f"Source validation run: {manifest['source_validation_run_id']}",
            f"Aircraft count: {manifest['aircraft_count']}",
            f"Feature rows: {manifest['row_counts']['features']}",
            f"Alert counts: {manifest['alert_counts']}",
            f"Status: {manifest['overall_status']}",
        ]
    )
