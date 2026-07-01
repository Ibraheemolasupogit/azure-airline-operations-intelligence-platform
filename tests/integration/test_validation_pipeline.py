from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import ValidationOutputCollisionError
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.validation.config import load_validation_config, with_overrides
from airline_operations_intelligence.validation.pipeline import validate_data, verify_validation_report_checksums
from airline_operations_intelligence.validation.reporting import describe_validation_manifest


def test_valid_generated_run_validates_and_writes_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("valid-source")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    result = validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="valid-validation")

    assert result.overall_status == "passed"
    assert result.severity_counts == {"info": 0, "warning": 0, "error": 0, "fatal": 0}
    for dataset, counts in result.row_counts.items():
        assert counts["source"] == counts["valid"]
        assert counts["quarantined"] == 0
        assert (result.processed_dir / dataset).exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_row_count"] == manifest["valid_row_count"]
    verify_validation_report_checksums(result.report_dir)
    metrics = list(csv.DictReader(result.metrics_path.open("r", encoding="utf-8", newline="")))
    assert {row["quality_dimension"] for row in metrics} >= {"validity", "integrity"}
    lineage = json.loads(result.lineage_path.read_text(encoding="utf-8"))
    assert lineage["future_azure_mapping"]["lineage"] == "Microsoft Purview"
    assert "valid-source" in result.summary_path.read_text(encoding="utf-8")
    assert "Overall status: passed" in describe_validation_manifest(result.report_dir)


def test_validation_collision_and_overwrite_are_controlled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("collision-source")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="collision")

    with pytest.raises(ValidationOutputCollisionError):
        validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="collision")

    overwritten = validate_data(
        source_run_dir=source.run_dir,
        config=with_overrides(config, overwrite=True),
        validation_run_id="collision",
    )

    assert overwritten.validation_run_id == "collision"


def test_corrupted_record_is_quarantined_with_rule_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("corrupt-source")
    _corrupt_schedule_airport_and_refresh_manifest(source.run_dir)
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    result = validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="corrupt-validation")

    assert result.overall_status == "failed"
    assert result.row_counts["flight_schedule.csv"]["quarantined"] == 1
    assert result.row_counts["flight_schedule.csv"]["valid"] == 23
    quarantine = result.interim_dir / "quarantine" / "flight_schedule_quarantine.jsonl"
    payload = json.loads(quarantine.read_text(encoding="utf-8").splitlines()[0])
    assert {"FS-005", "REL-001"}.issubset(set(payload["failed_rule_ids"]))
    assert payload["source_record"]["origin_airport"] == "ZZZ"


def test_fatal_source_integrity_failure_writes_no_successful_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("fatal-source")
    schedule = source.run_dir / "flight_schedule.csv"
    schedule.write_text(schedule.read_text(encoding="utf-8").replace("LHR", "ZZZ", 1), encoding="utf-8")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    with pytest.raises(Exception, match="Checksum mismatch"):
        validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="fatal-validation")

    assert not Path("reports/validation/fatal-validation").exists()
    assert not Path("data/processed/fatal-validation").exists()


def test_repeated_validation_reproduces_business_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("deterministic-source")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    first = validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="det-a")
    second = validate_data(source_run_dir=source.run_dir, config=config, validation_run_id="det-b")

    for dataset in first.row_counts:
        assert sha256_file(first.processed_dir / dataset) == sha256_file(second.processed_dir / dataset)
    assert _metrics_without_run_id(first.metrics_path) == _metrics_without_run_id(second.metrics_path)


def _generate_ci_source(run_id: str):
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    return generate_data(config, run_id=run_id)


def _corrupt_schedule_airport_and_refresh_manifest(run_dir: Path) -> None:
    path = run_dir / "flight_schedule.csv"
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    rows[0]["origin_airport"] = "ZZZ"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = run_dir / "generation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["datasets"]:
        if entry["filename"] == "flight_schedule.csv":
            entry["sha256"] = sha256_file(path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _metrics_without_run_id(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))
    for row in rows:
        row["validation_run_id"] = "<run>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
