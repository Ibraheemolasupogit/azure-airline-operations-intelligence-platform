"""Lineage for disruption scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.disruption.contracts import DisruptionSource
from airline_operations_intelligence.disruption.discovery import REQUIRED_PROCESSED


def build_lineage(
    *,
    disruption_run_id: str,
    source: DisruptionSource,
    output_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    timestamp_utc: str,
    package_version: str,
) -> dict[str, Any]:
    """Build disruption lineage."""
    optional_nodes = []
    for optional in (source.passenger_forecast, source.delay_prediction, source.maintenance_analytics):
        if optional is not None:
            optional_nodes.append(
                {
                    "node_id": f"{optional.source_type}:{optional.run_id}",
                    "node_type": "optional_upstream_analytics",
                    "path": optional.output_path.as_posix(),
                    "sha256": optional.output_sha256,
                }
            )
    return {
        "schema_version": "1.0",
        "disruption_run_id": disruption_run_id,
        "created_at_utc": timestamp_utc,
        "package_version": package_version,
        "config_fingerprint": config_fingerprint,
        "source_validation_run_id": source.validation_run_id,
        "nodes": [
            {
                "node_id": f"validation:{source.validation_run_id}",
                "node_type": "validation_run",
                "path": source.report_dir.as_posix(),
                "sha256": source.validation_manifest_sha256,
            },
            *[
                {
                    "node_id": f"processed:{name}",
                    "node_type": "processed_dataset",
                    "path": (source.processed_dir / name).as_posix(),
                    "sha256": source.processed_checksums[name],
                }
                for name in REQUIRED_PROCESSED
            ],
            *optional_nodes,
            {"node_id": "features:disruption", "node_type": "feature_table", "path": output_dir.as_posix()},
            {"node_id": "scoring:disruption", "node_type": "component_scoring", "path": output_dir.as_posix()},
            {"node_id": "alerts:disruption", "node_type": "alert_generation", "path": output_dir.as_posix()},
            {"node_id": "reports:disruption", "node_type": "reports", "path": report_dir.as_posix()},
        ],
        "future_azure_mapping": {
            "purview": "lineage export placeholder for a later milestone",
            "azure_ml": "batch scoring placeholder for a later milestone",
            "azure_data_explorer": "operational analytics placeholder for a later milestone",
            "azure_monitor": "monitoring placeholder for Milestone 8 or later",
            "power_bi": "dashboard output placeholder for Milestone 10 or later",
        },
    }
