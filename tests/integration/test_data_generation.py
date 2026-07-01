from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import OutputCollisionError
from airline_operations_intelligence.data_generation.config import load_generation_config, with_overrides
from airline_operations_intelligence.data_generation.manifest import verify_manifest_checksums
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.data_generation.writers import sha256_file

REQUIRED_DATASETS = {
    "flight_schedule.csv",
    "passenger_demand.csv",
    "weather_events.csv",
    "aircraft_health.jsonl",
    "crew_operations.csv",
    "delay_history.csv",
    "airport_events.jsonl",
}


def test_full_generation_outputs_are_relational_and_manifested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")

    result = generate_data(config, run_id="integration")

    assert result.run_dir == Path("data/raw/integration")
    assert result.run_dir.exists()
    for filename in REQUIRED_DATASETS | {
        "generation-manifest.json",
        "data-dictionary.json",
        "generation-summary.md",
    }:
        assert (result.run_dir / filename).exists()

    schedule = _read_csv(result.run_dir / "flight_schedule.csv")
    demand = _read_csv(result.run_dir / "passenger_demand.csv")
    crew = _read_csv(result.run_dir / "crew_operations.csv")
    delays = _read_csv(result.run_dir / "delay_history.csv")
    health = _read_jsonl(result.run_dir / "aircraft_health.jsonl")
    weather = _read_csv(result.run_dir / "weather_events.csv")
    airport_events = _read_jsonl(result.run_dir / "airport_events.jsonl")
    flight_ids = {row["flight_id"] for row in schedule}
    assert len(flight_ids) == len(schedule)
    assert {row["flight_id"] for row in demand} == flight_ids
    assert {row["flight_id"] for row in crew} == flight_ids
    assert {row["flight_id"] for row in delays} == flight_ids
    assert {row["flight_id"] for row in health} == flight_ids
    airport_codes = config.airport_codes
    assert {row["airport_code"] for row in weather}.issubset(airport_codes)
    assert {row["airport_code"] for row in airport_events}.issubset(airport_codes)

    manifest = json.loads((result.run_dir / "generation-manifest.json").read_text(encoding="utf-8"))
    manifest_counts = {entry["filename"]: entry["row_count"] for entry in manifest["datasets"]}
    assert manifest_counts["flight_schedule.csv"] == len(schedule)
    assert manifest_counts["passenger_demand.csv"] == len(demand)
    assert manifest_counts["aircraft_health.jsonl"] == len(health)
    for entry in manifest["datasets"]:
        assert sha256_file(result.run_dir / entry["filename"]) == entry["sha256"]
    verify_manifest_checksums(result.run_dir)

    dictionary = json.loads((result.run_dir / "data-dictionary.json").read_text(encoding="utf-8"))
    dictionary_pairs = {(field["dataset"], field["field_name"]) for field in dictionary["fields"]}
    for entry in manifest["datasets"]:
        for field_name in entry["field_names"]:
            assert (entry["filename"], field_name) in dictionary_pairs
    summary = (result.run_dir / "generation-summary.md").read_text(encoding="utf-8")
    assert "integration" in summary
    assert "flight_schedule.csv" in summary


def test_generation_is_reproducible_for_same_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")

    first = generate_data(config, run_id="same-a")
    second = generate_data(config, run_id="same-b")

    for filename in REQUIRED_DATASETS:
        assert sha256_file(first.run_dir / filename) == sha256_file(second.run_dir / filename)


def test_changed_seed_changes_business_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    changed = with_overrides(config, seed=config.settings.seed + 1)

    first = generate_data(config, run_id="seed-a")
    second = generate_data(changed, run_id="seed-b")

    assert any(
        sha256_file(first.run_dir / filename) != sha256_file(second.run_dir / filename)
        for filename in REQUIRED_DATASETS
    )


def test_generation_collision_and_overwrite_are_controlled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    generate_data(config, run_id="collision")

    with pytest.raises(OutputCollisionError):
        generate_data(config, run_id="collision")

    overwritten = generate_data(with_overrides(config, overwrite=True), run_id="collision")

    assert overwritten.run_dir == Path("data/raw/collision")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
