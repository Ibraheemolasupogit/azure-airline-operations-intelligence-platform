"""Lineage for maintenance analytics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.maintenance.contracts import MaintenanceSource
from airline_operations_intelligence.maintenance.discovery import REQUIRED_PROCESSED, SUPPORTING_PROCESSED


def build_lineage(
    *,
    maintenance_run_id: str,
    source: MaintenanceSource,
    output_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    timestamp_utc: str,
    package_version: str,
) -> dict[str, Any]:
    """Build deterministic lineage payload."""
    datasets = [name for name in (*REQUIRED_PROCESSED, *SUPPORTING_PROCESSED) if name in source.processed_checksums]
    return {
        "schema_version": "1.0",
        "maintenance_run_id": maintenance_run_id,
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
                for name in datasets
            ],
            {"node_id": "features:aircraft_health", "node_type": "feature_table", "path": output_dir.as_posix()},
            {"node_id": "scoring:maintenance_risk", "node_type": "scoring_step", "path": output_dir.as_posix()},
            {"node_id": "alerts:maintenance", "node_type": "alert_generation", "path": output_dir.as_posix()},
            {"node_id": "reports:maintenance", "node_type": "reports", "path": report_dir.as_posix()},
        ],
        "edges": [{"from": f"processed:{name}", "to": "features:aircraft_health"} for name in datasets]
        + [
            {"from": "features:aircraft_health", "to": "scoring:maintenance_risk"},
            {"from": "scoring:maintenance_risk", "to": "alerts:maintenance"},
            {"from": "alerts:maintenance", "to": "reports:maintenance"},
        ],
        "future_azure_mapping": {
            "azure_data_explorer": "telemetry analytics placeholder for a later milestone",
            "azure_ml": "batch analytics or model tracking placeholder for a later milestone",
            "azure_monitor": "alert routing placeholder for a later milestone",
            "purview": "lineage export placeholder for a later milestone",
        },
    }
