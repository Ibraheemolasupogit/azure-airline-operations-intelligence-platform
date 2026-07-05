from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import ForecastingSourceError, ForecastOutputCollisionError
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.forecasting.config import load_forecasting_config, with_overrides
from airline_operations_intelligence.forecasting.pipeline import forecast_passenger_demand
from airline_operations_intelligence.forecasting.reporting import describe_forecast_report
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.pipeline import validate_data


def test_passenger_forecasting_pipeline_outputs_and_determinism(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("forecast-source", "forecast-validation")
    config = load_forecasting_config(_repo_root() / "configs/passenger_forecasting_ci.yaml")

    first = forecast_passenger_demand(
        validation_report_dir=validation.report_dir,
        config=config,
        forecast_run_id="forecast-a",
    )
    second = forecast_passenger_demand(
        validation_report_dir=validation.report_dir,
        config=config,
        forecast_run_id="forecast-b",
    )

    assert first.overall_status == "passed"
    assert first.partition_row_counts["train"] > 0
    assert first.partition_row_counts["validation"] > 0
    assert first.partition_row_counts["test"] > 0
    assert first.champion_model_id in {"historical_mean", "seasonal_naive", "linear_regression"}
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_validation_run_id"] == "forecast-validation"
    assert manifest["prediction_grain"] == "one forecast per flight at configured booking horizon"
    assert "No forbidden" in manifest["leakage_checks"][0]
    assert (first.output_dir / "passenger_forecast.csv").exists()
    assert (first.model_dir / "champion-model.json").exists()
    assert (first.report_dir / "model-card.md").exists()
    assert "Forecast run ID" in describe_forecast_report(first.report_dir)
    _assert_forecasts_valid(first.forecast_path)
    assert _forecast_business_rows(first.forecast_path) == _forecast_business_rows(second.forecast_path)
    assert _metrics_without_run_id(first.metrics_path) == _metrics_without_run_id(second.metrics_path)


def test_forecast_collision_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("collision-source", "collision-validation")
    config = load_forecasting_config(_repo_root() / "configs/passenger_forecasting_ci.yaml")
    forecast_passenger_demand(validation_report_dir=validation.report_dir, config=config, forecast_run_id="collision")

    with pytest.raises(ForecastOutputCollisionError):
        forecast_passenger_demand(
            validation_report_dir=validation.report_dir,
            config=config,
            forecast_run_id="collision",
        )

    overwritten = forecast_passenger_demand(
        validation_report_dir=validation.report_dir,
        config=with_overrides(config, overwrite=True),
        forecast_run_id="collision",
    )

    assert overwritten.forecast_run_id == "collision"


def test_forecasting_rejects_failed_validation_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("failed-source", "failed-validation")
    manifest_path = validation.report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["overall_status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = load_forecasting_config(_repo_root() / "configs/passenger_forecasting_ci.yaml")

    with pytest.raises(ForecastingSourceError, match="not accepted"):
        forecast_passenger_demand(validation_report_dir=validation.report_dir, config=config, forecast_run_id="reject")


def _validated_source(source_run_id: str, validation_run_id: str):
    generation_config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    source = generate_data(generation_config, run_id=source_run_id)
    validation_config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    return validate_data(
        source_run_dir=source.run_dir,
        config=validation_config,
        validation_run_id=validation_run_id,
    )


def _assert_forecasts_valid(path: Path) -> None:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    assert rows
    for row in rows:
        forecast = float(row["forecast_passengers"])
        assert forecast >= 0
        assert forecast <= float(row["allowed_capacity"])
        assert float(row["forecast_lower_80"]) <= forecast <= float(row["forecast_upper_80"])
        assert float(row["forecast_lower_95"]) <= forecast <= float(row["forecast_upper_95"])


def _metrics_without_run_id(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        row["forecast_run_id"] = "<run>"
    return rows


def _forecast_business_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        row["forecast_run_id"] = "<run>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
