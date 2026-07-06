"""Lineage graph for delay prediction runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.delay_prediction.contracts import DelayPredictionSource
from airline_operations_intelligence.delay_prediction.discovery import REQUIRED_PROCESSED


def build_lineage(
    *,
    delay_run_id: str,
    source: DelayPredictionSource,
    output_dir: Path,
    model_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    champion_model_id: str,
    timestamp_utc: str,
) -> dict[str, Any]:
    """Build deterministic lineage payload."""
    source_nodes = [
        {
            "node_id": f"processed:{filename}",
            "node_type": "processed_dataset",
            "path": (source.processed_dir / filename).as_posix(),
            "sha256": source.processed_checksums[filename],
        }
        for filename in REQUIRED_PROCESSED
    ]
    if source.passenger_forecast is not None:
        source_nodes.append(
            {
                "node_id": "forecast:passenger_demand",
                "node_type": "optional_forecast",
                "path": source.passenger_forecast.forecast_path.as_posix(),
                "sha256": source.passenger_forecast.forecast_sha256,
            }
        )
    return {
        "schema_version": "1.0",
        "delay_run_id": delay_run_id,
        "created_at_utc": timestamp_utc,
        "config_fingerprint": config_fingerprint,
        "source_validation_run_id": source.validation_run_id,
        "champion_model_id": champion_model_id,
        "nodes": [
            {
                "node_id": f"validation:{source.validation_run_id}",
                "node_type": "validation_run",
                "path": source.report_dir.as_posix(),
                "sha256": source.validation_manifest_sha256,
            },
            *source_nodes,
            {"node_id": "features:delay_model_table", "node_type": "feature_table", "path": "in-memory"},
            {"node_id": f"model:{champion_model_id}", "node_type": "local_model", "path": model_dir.as_posix()},
            {"node_id": "predictions:flight_delay", "node_type": "prediction_output", "path": output_dir.as_posix()},
            {"node_id": "reports:delay_prediction", "node_type": "model_report", "path": report_dir.as_posix()},
        ],
        "edges": [
            {"from": f"processed:{filename}", "to": "features:delay_model_table"} for filename in REQUIRED_PROCESSED
        ]
        + [
            {"from": "features:delay_model_table", "to": f"model:{champion_model_id}"},
            {"from": f"model:{champion_model_id}", "to": "predictions:flight_delay"},
            {"from": "predictions:flight_delay", "to": "reports:delay_prediction"},
        ],
        "future_azure_mapping": {
            "azure_ml": "model registration placeholder for a later milestone",
            "purview": "lineage export placeholder for a later milestone",
        },
    }
