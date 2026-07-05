"""Forecasting lineage construction."""

from __future__ import annotations

from pathlib import Path

from airline_operations_intelligence.forecasting.contracts import ForecastingSource


def build_lineage(
    *,
    forecast_run_id: str,
    source: ForecastingSource,
    output_dir: Path,
    model_dir: Path,
    report_dir: Path,
    config_fingerprint: str,
    champion_model_id: str,
    timestamp_utc: str,
) -> dict[str, object]:
    """Build explicit forecasting lineage."""
    return {
        "schema_version": "1.0",
        "forecast_run_id": forecast_run_id,
        "source_validation_run_id": source.validation_run_id,
        "forecasting_configuration_fingerprint": config_fingerprint,
        "captured_at_utc": timestamp_utc,
        "nodes": [
            {
                "id": f"validation:{source.validation_run_id}",
                "type": "validation_run",
                "path": source.report_dir.as_posix(),
            },
            {
                "id": "processed:passenger_demand.csv",
                "type": "processed_dataset",
                "path": (source.processed_dir / "passenger_demand.csv").as_posix(),
                "sha256": source.processed_checksums["passenger_demand.csv"],
            },
            {
                "id": "processed:flight_schedule.csv",
                "type": "processed_dataset",
                "path": (source.processed_dir / "flight_schedule.csv").as_posix(),
                "sha256": source.processed_checksums["flight_schedule.csv"],
            },
            {"id": "feature-table", "type": "forecast_feature_table"},
            {"id": f"model:{champion_model_id}", "type": "champion_model", "path": model_dir.as_posix()},
            {
                "id": "forecast-output",
                "type": "forecast_csv",
                "path": (output_dir / "passenger_forecast.csv").as_posix(),
            },
            {"id": "forecast-report", "type": "forecast_reports", "path": report_dir.as_posix()},
        ],
        "edges": [
            {
                "from": f"validation:{source.validation_run_id}",
                "to": "processed:passenger_demand.csv",
                "relationship": "produced",
            },
            {
                "from": f"validation:{source.validation_run_id}",
                "to": "processed:flight_schedule.csv",
                "relationship": "produced",
            },
            {"from": "processed:passenger_demand.csv", "to": "feature-table", "relationship": "features_from"},
            {"from": "processed:flight_schedule.csv", "to": "feature-table", "relationship": "features_from"},
            {"from": "feature-table", "to": f"model:{champion_model_id}", "relationship": "trains"},
            {"from": f"model:{champion_model_id}", "to": "forecast-output", "relationship": "predicts"},
            {"from": "forecast-output", "to": "forecast-report", "relationship": "evidenced_by"},
        ],
        "future_azure_mapping": {
            "training": "Azure Machine Learning command jobs",
            "model_registry": "Azure ML model registry candidate",
            "forecast_output": "ADLS Gen2, Synapse, Fabric, or downstream Power BI dataset",
            "lineage": "Azure ML lineage and Microsoft Purview",
        },
    }
