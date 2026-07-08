"""Lineage construction for monitoring runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.monitoring.contracts import MonitoringSource


def build_lineage(
    *,
    monitoring_run_id: str,
    source: MonitoringSource,
    output_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    checks_executed: list[str],
    metrics_produced: list[str],
    alerts_produced: int,
    artefact_checksums: dict[str, str],
    timestamp_utc: str,
    package_version: str,
) -> dict[str, Any]:
    """Build monitoring lineage payload."""
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "monitoring_run_id": monitoring_run_id,
        "source_generation_run_id": source.generation_run_id,
        "source_validation_run_id": source.validation_run_id,
        "optional_inputs": {
            domain: manifest.get(_run_id_key(domain)) for domain, manifest in sorted(source.optional_manifests.items())
        },
        "baseline_monitoring_run_id": source.baseline_manifest.get("monitoring_run_id")
        if source.baseline_manifest
        else None,
        "input_manifest_checksums": source.input_manifest_checksums,
        "input_artefact_checksums_verified": source.input_artefact_checksums_verified,
        "monitoring_configuration_fingerprint": config_fingerprint,
        "checks_executed": checks_executed,
        "metrics_produced": metrics_produced,
        "alerts_produced": alerts_produced,
        "outputs": output_dir.as_posix(),
        "reports": report_dir.as_posix(),
        "artefact_checksums": artefact_checksums,
        "package_version": package_version,
        "timestamp_utc": timestamp_utc,
        "future_azure_mappings": {
            "Azure Monitor": "custom metrics and alert rules in a future deployment milestone",
            "Log Analytics": "monitoring metrics, checks, and alerts as future tables",
            "Application Insights": "application telemetry mapping only; no client is implemented",
            "Azure Data Explorer": "operational telemetry summaries in a future analytics store",
            "Microsoft Purview": "lineage registration in a future governance milestone",
            "Power BI": "dashboard-ready summaries for Milestone 10",
            "Azure Machine Learning": "model and analytics evidence metrics in a future production mapping",
        },
        "synthetic_data_declaration": "Monitoring lineage references fictional synthetic aviation data only.",
    }


def _run_id_key(domain: str) -> str:
    return {
        "passenger_forecasting": "forecast_run_id",
        "delay_prediction": "delay_run_id",
        "maintenance_analytics": "maintenance_run_id",
        "disruption_scoring": "disruption_run_id",
    }[domain]
