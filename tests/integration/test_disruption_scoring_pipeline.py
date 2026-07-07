from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    DisruptionOutputCollisionError,
    DisruptionScoringSourceError,
)
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.disruption.config import load_disruption_config, with_overrides
from airline_operations_intelligence.disruption.pipeline import score_disruptions
from airline_operations_intelligence.disruption.reporting import describe_disruption_report
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.pipeline import validate_data


def test_disruption_pipeline_outputs_and_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("disruption-source", "disruption-validation")
    config = load_disruption_config(_repo_root() / "configs/disruption_scoring_ci.yaml")

    first = score_disruptions(
        validation_report_dir=validation.report_dir, config=config, disruption_run_id="disruption-a"
    )
    second = score_disruptions(
        validation_report_dir=validation.report_dir, config=config, disruption_run_id="disruption-b"
    )

    assert first.overall_status == "passed"
    assert first.row_counts["features"] == 24
    assert first.row_counts["scores"] == 24
    assert first.row_counts["alerts"] == 12
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_validation_run_id"] == "disruption-validation"
    assert manifest["artefact_checksums"]["disruption_scores.csv"] == sha256_file(first.scores_path)
    assert (first.output_dir / "route_disruption_summary.csv").exists()
    assert (first.report_dir / "lineage.json").exists()
    assert "Disruption scoring run" in describe_disruption_report(first.report_dir)
    _assert_scores(first.scores_path)
    _assert_alerts(first.alerts_path)
    assert _normalised_csv(first.scores_path) == _normalised_csv(second.scores_path)
    assert _normalised_csv(first.output_dir / "daily_disruption_summary.csv") == _normalised_csv(
        second.output_dir / "daily_disruption_summary.csv"
    )


def test_disruption_collision_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("disruption-collision-source", "disruption-collision-validation")
    config = load_disruption_config(_repo_root() / "configs/disruption_scoring_ci.yaml")
    score_disruptions(validation_report_dir=validation.report_dir, config=config, disruption_run_id="collision")

    with pytest.raises(DisruptionOutputCollisionError):
        score_disruptions(validation_report_dir=validation.report_dir, config=config, disruption_run_id="collision")

    overwritten = score_disruptions(
        validation_report_dir=validation.report_dir,
        config=with_overrides(config, overwrite=True),
        disruption_run_id="collision",
    )
    assert overwritten.disruption_run_id == "collision"


def test_disruption_rejects_failed_validation_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    validation = _validated_source("disruption-failed-source", "disruption-failed-validation")
    manifest_path = validation.report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["overall_status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = load_disruption_config(_repo_root() / "configs/disruption_scoring_ci.yaml")

    with pytest.raises(DisruptionScoringSourceError, match="not accepted"):
        score_disruptions(validation_report_dir=validation.report_dir, config=config, disruption_run_id="reject")


def _validated_source(source_run_id: str, validation_run_id: str):
    generation_config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    source = generate_data(generation_config, run_id=source_run_id)
    validation_config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    return validate_data(source_run_dir=source.run_dir, config=validation_config, validation_run_id=validation_run_id)


def _assert_scores(path: Path) -> None:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    assert len({row["flight_id"] for row in rows}) == len(rows)
    for row in rows:
        assert 0 <= float(row["disruption_severity_score"]) <= 1
        assert 0 <= float(row["forward_disruption_risk_score"]) <= 1
        assert 0 <= float(row["retrospective_disruption_score"]) <= 1
        assert row["disruption_risk_band"] in {"low", "medium", "high", "severe"}
        assert row["recovery_priority"] in {"monitor", "review", "prioritise", "urgent_review"}


def _assert_alerts(path: Path) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    assert len({row["alert_id"] for row in rows}) == len(rows)
    assert all(row["human_review_required"] for row in rows)


def _normalised_csv(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        if "disruption_run_id" in row:
            row["disruption_run_id"] = "<run>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
