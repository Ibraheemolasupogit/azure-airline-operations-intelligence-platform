"""Dashboard-output lineage generation."""

from __future__ import annotations

from typing import Any

from airline_operations_intelligence.dashboard.contracts import DashboardSource


def build_lineage(source: DashboardSource, run_id: str, checksums: dict[str, str]) -> dict[str, Any]:
    """Build local lineage for dashboard outputs and future Microsoft mappings."""
    return {
        "dashboard_run_id": run_id,
        "lineage": [
            {
                "stage": "Milestone 2 generation run",
                "run_id": source.validation.manifest.get("source_generation_run_id"),
            },
            {"stage": "Milestone 3 validation run", "run_id": source.validation.run_id},
            {"stage": "Milestone 7 disruption scoring", "run_id": source.disruption.run_id},
            {"stage": "Milestone 8 monitoring", "run_id": source.monitoring.run_id},
            {
                "stage": "Optional analytics and assistant",
                "run_ids": {domain: artefact.run_id for domain, artefact in source.optional.items()},
            },
            {"stage": "Manifest and checksum verification", "status": "passed"},
            {"stage": "Dimension and fact transformations", "status": "passed"},
            {"stage": "KPI generation", "status": "passed"},
            {"stage": "Semantic model, measures, page specs, dictionary", "status": "passed"},
            {"stage": "Dashboard manifest and reports", "artefact_count": len(checksums)},
        ],
        "future_microsoft_mapping": {
            "power_bi": "Semantic model specification and measure catalogue can inform a future Power BI model.",
            "fabric": "CSV/JSON exports can map to Fabric Lakehouse curated tables later.",
            "adls_gen2": "Local dashboard CSV outputs can map to a curated dashboard zone.",
            "synapse": "Fact and dimension tables can be external tables in a later milestone.",
            "azure_data_explorer": "Monitoring and disruption facts can map to analytical tables later.",
            "purview": "This lineage JSON can map to future Microsoft Purview lineage.",
        },
        "artefact_checksums": dict(sorted(checksums.items())),
    }
