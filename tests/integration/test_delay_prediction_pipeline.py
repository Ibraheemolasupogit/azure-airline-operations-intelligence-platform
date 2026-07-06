from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    DelayOutputCollisionError,
    DelayPredictionSourceError,
)
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.delay_prediction.config import load_delay_prediction_config, with_overrides
from airline_operations_intelligence.delay_prediction.pipeline import predict_flight_delays
from airline_operations_intelligence.delay_prediction.reporting import describe_delay_prediction_report
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.pipeline import validate_data


def test_delay_prediction_pipeline_outputs_and_determinism(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("delay-source", "delay-validation")
    config = load_delay_prediction_config(_repo_root() / "configs/delay_prediction_ci.yaml")

    first = predict_flight_delays(validation_report_dir=validation.report_dir, config=config, delay_run_id="delay-a")
    second = predict_flight_delays(validation_report_dir=validation.report_dir, config=config, delay_run_id="delay-b")

    assert first.overall_status == "passed"
    assert first.partition_row_counts == {"train": 14, "validation": 4, "test": 6}
    assert first.champion_model_id in {
        "majority_class_baseline",
        "route_historical_rate_baseline",
        "logistic_regression",
    }
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_validation_run_id"] == "delay-validation"
    assert manifest["target"]["prediction_grain"] == "scheduled_flight"
    assert "Feature names exclude" in manifest["leakage_checks"][0]
    assert (first.output_dir / "delay_predictions.csv").exists()
    assert (first.model_dir / "champion-model.json").exists()
    assert (first.report_dir / "model-card.md").exists()
    assert "Delay prediction run" in describe_delay_prediction_report(first.report_dir)
    _assert_predictions_valid(first.predictions_path)
    assert _business_rows(first.predictions_path) == _business_rows(second.predictions_path)
    assert _metrics_rows(first.metrics_path) == _metrics_rows(second.metrics_path)


def test_delay_prediction_collision_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("delay-collision-source", "delay-collision-validation")
    config = load_delay_prediction_config(_repo_root() / "configs/delay_prediction_ci.yaml")
    predict_flight_delays(validation_report_dir=validation.report_dir, config=config, delay_run_id="collision")

    with pytest.raises(DelayOutputCollisionError):
        predict_flight_delays(validation_report_dir=validation.report_dir, config=config, delay_run_id="collision")

    overwritten = predict_flight_delays(
        validation_report_dir=validation.report_dir,
        config=with_overrides(config, overwrite=True),
        delay_run_id="collision",
    )

    assert overwritten.delay_run_id == "collision"


def test_delay_prediction_rejects_failed_validation_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("delay-failed-source", "delay-failed-validation")
    manifest_path = validation.report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["overall_status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = load_delay_prediction_config(_repo_root() / "configs/delay_prediction_ci.yaml")

    with pytest.raises(DelayPredictionSourceError, match="not accepted"):
        predict_flight_delays(validation_report_dir=validation.report_dir, config=config, delay_run_id="reject")


def _validated_source(source_run_id: str, validation_run_id: str):
    generation_config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    source = generate_data(generation_config, run_id=source_run_id)
    validation_config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    return validate_data(source_run_dir=source.run_dir, config=validation_config, validation_run_id=validation_run_id)


def _assert_predictions_valid(path: Path) -> None:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    assert rows
    assert len({row["flight_id"] for row in rows}) == len(rows)
    for row in rows:
        probability = float(row["delay_probability"])
        assert 0 <= probability <= 1
        assert row["risk_band"] in {"low", "medium", "high"}
        assert float(row["estimated_delay_minutes"]) >= 0


def _metrics_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def _business_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        row["delay_run_id"] = "<run>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
