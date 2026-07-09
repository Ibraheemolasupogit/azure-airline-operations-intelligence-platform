"""Markdown reports and completed run descriptions for dashboard outputs."""

from __future__ import annotations

from pathlib import Path

from airline_operations_intelligence.common.exceptions import DashboardArtefactError
from airline_operations_intelligence.dashboard.artefacts import read_json


def build_summary(manifest: dict[str, object]) -> str:
    """Build dashboard output summary markdown."""
    rows = manifest.get("row_counts", {})
    lines = [
        "# Dashboard Output Summary",
        "",
        f"Dashboard run: {manifest['dashboard_run_id']}",
        f"Validation source: {manifest['source_validation_run_id']}",
        f"Disruption source: {manifest['source_disruption_run_id']}",
        f"Monitoring source: {manifest['source_monitoring_run_id']}",
        "",
        "## Row Counts",
        "",
    ]
    if isinstance(rows, dict):
        lines.extend(f"- {name}: {count}" for name, count in sorted(rows.items()))
    lines.extend(
        [
            "",
            "## Quality",
            "",
            f"Overall status: {manifest['overall_status']}",
            f"Quality summary: {manifest['quality_check_summary']}",
            "",
            "Synthetic data only. Local dashboard-ready exports; no Power BI, Fabric, Azure, or external publishing.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_semantic_report(manifest: dict[str, object]) -> str:
    """Build semantic model report markdown."""
    tables_created = manifest.get("tables_created", [])
    table_count = len(tables_created) if isinstance(tables_created, list) else 0
    return (
        "# Semantic Model Report\n\n"
        "The dashboard layer exports a star-schema style local model with dimensions, facts, KPI tables, "
        "summaries, documented relationships, and recommended measures.\n\n"
        f"Tables created: {table_count}\n\n"
        "Power BI/Fabric consumption guidance: import CSV/JSON outputs as curated tables, implement the "
        "documented relationships with single-direction filters, and use the measure catalogue as DAX design "
        "documentation. No `.pbix` or live semantic model is generated in Milestone 10.\n"
    )


def build_governance_report(manifest: dict[str, object]) -> str:
    """Build dashboard governance report markdown."""
    return (
        "# Dashboard Governance Report\n\n"
        "Intended use: local synthetic-data dashboard prototyping and evidence review.\n\n"
        "Out-of-scope use: live operations control, certified airline reporting, passenger, crew, engineering, "
        "or operational decisions.\n\n"
        "No-live-cloud-publishing statement: this workflow does not call Power BI APIs, Fabric APIs, Azure APIs, "
        "OpenAI APIs, or external services.\n\n"
        f"Source artefacts: validation={manifest['source_validation_run_id']}, "
        f"disruption={manifest['source_disruption_run_id']}, "
        f"monitoring={manifest['source_monitoring_run_id']}.\n\n"
        "Future mapping: local CSV outputs to ADLS Gen2 or Fabric Lakehouse tables; semantic-model JSON to future "
        "Power BI/Tabular model design; lineage JSON to Microsoft Purview.\n"
    )


def pages_markdown(pages: list[dict[str, object]]) -> str:
    """Render page specs to markdown."""
    lines = ["# Dashboard Page Specifications", ""]
    for page in pages:
        lines.extend([f"## {page['page_name']}", "", str(page["purpose"]), ""])
    return "\n".join(lines) + "\n"


def measures_markdown(measures: list[dict[str, str]]) -> str:
    """Render measure catalogue markdown."""
    lines = ["# Measure Catalogue", "", "| Measure | Source Table | Expression |", "| --- | --- | --- |"]
    for measure in measures:
        lines.append(f"| {measure['measure_name']} | {measure['source_table']} | `{measure['dax_expression']}` |")
    return "\n".join(lines) + "\n"


def describe_dashboard_report(dashboard_report_dir: Path) -> str:
    """Describe a completed dashboard-output run without rebuilding."""
    manifest_path = dashboard_report_dir / "dashboard-output-manifest.json"
    if not manifest_path.is_file():
        raise DashboardArtefactError(f"Dashboard manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    return (
        f"Dashboard run: {manifest['dashboard_run_id']}\n"
        f"Validation source: {manifest['source_validation_run_id']}\n"
        f"Disruption source: {manifest['source_disruption_run_id']}\n"
        f"Monitoring source: {manifest['source_monitoring_run_id']}\n"
        f"Tables created: {len(manifest.get('tables_created', []))}\n"
        f"Measures: {manifest.get('measure_count', 0)}\n"
        f"Pages: {manifest.get('page_spec_count', 0)}\n"
        f"Overall status: {manifest['overall_status']}"
    )
