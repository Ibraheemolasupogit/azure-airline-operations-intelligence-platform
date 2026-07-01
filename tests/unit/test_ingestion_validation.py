from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import SourceIntegrityError
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.ingestion.discovery import discover_source_run
from airline_operations_intelligence.ingestion.normalization import normalize_value
from airline_operations_intelligence.ingestion.readers import read_source_dataset
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.models import FieldSpec


def test_source_discovery_and_readers_load_all_datasets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("reader-source")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    discovered = discover_source_run(source.run_dir, config)

    assert discovered.run_id == "reader-source"
    assert set(discovered.datasets) == {
        "flight_schedule.csv",
        "passenger_demand.csv",
        "weather_events.csv",
        "aircraft_health.jsonl",
        "crew_operations.csv",
        "delay_history.csv",
        "airport_events.jsonl",
    }
    assert len(read_source_dataset(discovered.datasets["flight_schedule.csv"])) == 24
    assert len(read_source_dataset(discovered.datasets["aircraft_health.jsonl"])) == 24


def test_source_discovery_rejects_checksum_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    source = _generate_ci_source("checksum-source")
    schedule = source.run_dir / "flight_schedule.csv"
    schedule.write_text(schedule.read_text(encoding="utf-8").replace("LHR", "ZZZ", 1), encoding="utf-8")
    config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")

    with pytest.raises(SourceIntegrityError, match="Checksum mismatch"):
        discover_source_run(source.run_dir, config)


def test_normalization_rejects_bad_timestamp_and_boolean() -> None:
    timestamp, timestamp_error = normalize_value("2025-01-01T10:00:00", FieldSpec("ts", "timestamp"))
    boolean, boolean_error = normalize_value("yes", FieldSpec("flag", "boolean"))

    assert timestamp is None
    assert "timezone" in str(timestamp_error)
    assert boolean is None
    assert "true or false" in str(boolean_error)


def _generate_ci_source(run_id: str):
    config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    return generate_data(config, run_id=run_id)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
