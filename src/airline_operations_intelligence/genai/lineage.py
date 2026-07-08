"""Lineage construction for assistant runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.genai.contracts import AssistantSource, EvidenceItem, RetrievalDecision


def build_lineage(
    *,
    assistant_run_id: str,
    intent: str,
    source: AssistantSource,
    evidence: list[EvidenceItem],
    retrieval: list[RetrievalDecision],
    artefact_checksums: dict[str, str],
    output_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    package_version: str,
    timestamp_utc: str,
) -> dict[str, Any]:
    """Build assistant lineage payload."""
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "assistant_run_id": assistant_run_id,
        "intent": intent,
        "source_generation_run_id": source.generation_run_id,
        "source_validation_run_id": source.validation_run_id,
        "optional_runs": {
            domain: _run_id(domain, manifest) for domain, manifest in sorted(source.optional_manifests.items())
        },
        "input_manifest_checksums": source.input_manifest_checksums,
        "input_artefact_checksums_verified": source.input_artefact_checksums_verified,
        "configuration_fingerprint": config_fingerprint,
        "evidence_ids": [item.evidence_id for item in evidence],
        "retrieval_decisions": [decision.__dict__ for decision in retrieval],
        "outputs": output_dir.as_posix(),
        "reports": report_dir.as_posix(),
        "artefact_checksums": artefact_checksums,
        "package_version": package_version,
        "timestamp_utc": timestamp_utc,
        "future_mappings": {
            "Azure AI Foundry": "future prompt flow or agent workflow",
            "Azure OpenAI": "future model call replacing local deterministic templates",
            "Prompt Flow": "future prompt assembly and evaluation orchestration",
            "Azure Monitor": "future prompt, response, and guardrail audit telemetry",
            "Microsoft Purview": "future lineage registration",
            "Power BI": "future assistant summaries in Milestone 10",
        },
        "synthetic_data_declaration": "Assistant lineage references fictional synthetic aviation data only.",
    }


def _run_id(domain: str, manifest: dict[str, Any]) -> str | None:
    keys = {
        "passenger_forecasting": "forecast_run_id",
        "delay_prediction": "delay_run_id",
        "maintenance_analytics": "maintenance_run_id",
        "disruption_scoring": "disruption_run_id",
        "monitoring": "monitoring_run_id",
    }
    return str(manifest.get(keys[domain])) if manifest.get(keys[domain]) is not None else None
