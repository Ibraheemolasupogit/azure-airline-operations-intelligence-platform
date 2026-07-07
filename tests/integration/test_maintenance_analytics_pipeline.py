from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    MaintenanceAnalyticsSourceError,
    MaintenanceOutputCollisionError,
)
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.maintenance.config import load_maintenance_config, with_overrides
from airline_operations_intelligence.maintenance.pipeline import analyse_aircraft_health
from airline_operations_intelligence.maintenance.reporting import describe_aircraft_health_report
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.pipeline import validate_data


def test_maintenance_pipeline_outputs_and_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("maintenance-source", "maintenance-validation")
    config = load_maintenance_config(_repo_root() / "configs/maintenance_analytics_ci.yaml")

    first = analyse_aircraft_health(
        validation_report_dir=validation.report_dir,
        config=config,
        maintenance_run_id="maintenance-a",
    )
    second = analyse_aircraft_health(
        validation_report_dir=validation.report_dir,
        config=config,
        maintenance_run_id="maintenance-b",
    )

    assert first.overall_status == "passed"
    assert first.row_counts["features"] == 24
    assert first.row_counts["scores"] == 24
    assert first.row_counts["flight_risk"] == 24
    assert first.row_counts["aircraft_summary"] == 3
    assert first.row_counts["alerts"] > 0
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_validation_run_id"] == "maintenance-validation"
    assert manifest["row_counts"]["features"] == 24
    assert manifest["artefact_checksums"]["aircraft_health_scores.csv"] == sha256_file(first.scores_path)
    assert (first.output_dir / "aircraft_health_features.csv").exists()
    assert (first.output_dir / "maintenance_alerts.jsonl").exists()
    assert (first.report_dir / "lineage.json").exists()
    assert "Maintenance analytics run" in describe_aircraft_health_report(first.report_dir)
    _assert_scores(first.scores_path)
    _assert_alerts(first.alerts_path)
    assert _normalised_csv(first.scores_path, "maintenance_run_id") == _normalised_csv(
        second.scores_path, "maintenance_run_id"
    )
    assert _normalised_csv(first.output_dir / "aircraft_health_summary.csv", "maintenance_run_id") == _normalised_csv(
        second.output_dir / "aircraft_health_summary.csv", "maintenance_run_id"
    )


def test_maintenance_collision_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("maintenance-collision-source", "maintenance-collision-validation")
    config = load_maintenance_config(_repo_root() / "configs/maintenance_analytics_ci.yaml")
    analyse_aircraft_health(validation_report_dir=validation.report_dir, config=config, maintenance_run_id="collision")

    with pytest.raises(MaintenanceOutputCollisionError):
        analyse_aircraft_health(
            validation_report_dir=validation.report_dir, config=config, maintenance_run_id="collision"
        )

    overwritten = analyse_aircraft_health(
        validation_report_dir=validation.report_dir,
        config=with_overrides(config, overwrite=True),
        maintenance_run_id="collision",
    )
    assert overwritten.maintenance_run_id == "collision"


def test_maintenance_rejects_failed_validation_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("maintenance-failed-source", "maintenance-failed-validation")
    manifest_path = validation.report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["overall_status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = load_maintenance_config(_repo_root() / "configs/maintenance_analytics_ci.yaml")

    with pytest.raises(MaintenanceAnalyticsSourceError, match="not accepted"):
        analyse_aircraft_health(validation_report_dir=validation.report_dir, config=config, maintenance_run_id="reject")


def _validated_source(source_run_id: str, validation_run_id: str):
    generation_config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    source = generate_data(generation_config, run_id=source_run_id)
    validation_config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    return validate_data(source_run_dir=source.run_dir, config=validation_config, validation_run_id=validation_run_id)


def _assert_scores(path: Path) -> None:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    assert len({row["telemetry_id"] for row in rows}) == len(rows)
    for row in rows:
        assert 0 <= float(row["maintenance_risk_score"]) <= 1
        assert 0 <= float(row["aircraft_health_score"]) <= 1
        assert row["risk_band"] in {"low", "medium", "high"}
        assert row["alert_category"] in {"none", "advisory", "watch", "action_recommended"}


def _assert_alerts(path: Path) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert len({row["alert_id"] for row in rows}) == len(rows)
    assert all(row["human_review_required"] for row in rows)


def _normalised_csv(path: Path, run_id_field: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        row[run_id_field] = "<run>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
