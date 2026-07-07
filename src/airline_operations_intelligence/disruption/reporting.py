"""Markdown reports for disruption scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import DisruptionArtefactError


def build_summary(manifest: dict[str, Any]) -> str:
    """Build disruption summary."""
    return "\n".join(
        [
            "# Disruption Scoring Summary",
            "",
            f"- Run ID: `{manifest['disruption_run_id']}`",
            f"- Source validation run: `{manifest['source_validation_run_id']}`",
            f"- Flight count: `{manifest['row_counts']['scores']}`",
            f"- Optional inputs used: `{manifest['optional_inputs_used']}`",
            f"- Risk bands: `{manifest['risk_band_counts']}`",
            f"- Recovery priorities: `{manifest['recovery_priority_counts']}`",
            f"- Alerts: `{manifest['alert_counts']}`",
            "",
            "Decision-support scoring only; no autonomous recovery action is implemented.",
            "",
        ]
    )


def build_evidence_report(manifest: dict[str, Any]) -> str:
    """Build disruption evidence report."""
    return "\n".join(
        [
            "# Disruption Evidence Report",
            "",
            f"- Component weights: `{manifest['component_weights']}`",
            f"- Component score summary: `{manifest['component_score_summary']}`",
            f"- Highest-risk flights: `{manifest['highest_risk_flights']}`",
            "",
            "Scores combine delay, weather, airport, crew, aircraft-health, passenger-pressure, and network evidence.",
            "",
        ]
    )


def build_governance_report(manifest: dict[str, Any]) -> str:
    """Build disruption governance report."""
    return "\n".join(
        [
            "# Disruption Governance Report",
            "",
            "## Intended Use",
            "Synthetic portfolio analytics for operational disruption evidence.",
            "",
            "## Out Of Scope",
            "Certified operations control, air-traffic control, autonomous recovery optimisation,",
            "passenger-care automation,",
            "or dispatch authority.",
            "",
            f"- Configuration fingerprint: `{manifest['configuration_fingerprint']}`",
            f"- Timing policy: {manifest['timing_and_leakage_policy']}",
            f"- Responsible-use disclaimer: {manifest['responsible_use_disclaimer']}",
            "",
        ]
    )


def describe_disruption_report(report_dir: Path) -> str:
    """Describe a completed disruption scoring run."""
    manifest_path = report_dir / "disruption-scoring-manifest.json"
    if not manifest_path.is_file():
        raise DisruptionArtefactError(f"Disruption scoring manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Disruption scoring run: {manifest['disruption_run_id']}",
            f"Source validation run: {manifest['source_validation_run_id']}",
            f"Flight count: {manifest['row_counts']['scores']}",
            f"Risk bands: {manifest['risk_band_counts']}",
            f"Recovery priorities: {manifest['recovery_priority_counts']}",
            f"Status: {manifest['overall_status']}",
        ]
    )
