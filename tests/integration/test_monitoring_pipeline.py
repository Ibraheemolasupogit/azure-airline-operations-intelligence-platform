from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    MonitoringCompatibilityError,
    MonitoringIntegrityError,
    MonitoringOutputCollisionError,
    MonitoringSourceError,
)
from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.delay_prediction.config import load_delay_prediction_config
from airline_operations_intelligence.delay_prediction.pipeline import predict_flight_delays
from airline_operations_intelligence.disruption.config import load_disruption_config
from airline_operations_intelligence.disruption.pipeline import score_disruptions
from airline_operations_intelligence.forecasting.config import load_forecasting_config
from airline_operations_intelligence.forecasting.pipeline import forecast_passenger_demand
from airline_operations_intelligence.maintenance.config import load_maintenance_config
from airline_operations_intelligence.maintenance.pipeline import analyse_aircraft_health
from airline_operations_intelligence.monitoring.config import load_monitoring_config, with_overrides
from airline_operations_intelligence.monitoring.pipeline import monitor_platform
from airline_operations_intelligence.monitoring.reporting import describe_monitoring_report
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.config import with_overrides as with_validation_overrides
from airline_operations_intelligence.validation.pipeline import validate_data


def test_monitoring_pipeline_outputs_drift_and_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("monitor-source", "monitor-validation", "monitor-upstream")
    config = load_monitoring_config(_repo_root() / "configs/monitoring_ci.yaml")

    first = monitor_platform(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        passenger_forecast_report_dir=artefacts["forecast_report_dir"],
        delay_prediction_report_dir=artefacts["delay_report_dir"],
        maintenance_report_dir=artefacts["maintenance_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        config=config,
        monitoring_run_id="monitor-a",
    )
    second = monitor_platform(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        passenger_forecast_report_dir=artefacts["forecast_report_dir"],
        delay_prediction_report_dir=artefacts["delay_report_dir"],
        maintenance_report_dir=artefacts["maintenance_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        config=config,
        monitoring_run_id="monitor-b",
    )
    drifted = monitor_platform(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        baseline_monitoring_report_dir=first.report_dir,
        config=config,
        monitoring_run_id="monitor-drift",
    )

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert first.overall_status == "passed"
    assert first.row_counts == {"metrics": 42, "checks": 19, "alerts": 0, "domains": 6, "drift": 1}
    assert manifest["input_artefact_checksums_verified"]["validation"]
    assert manifest["artefact_checksums"]["monitoring-metrics.csv"] == sha256_file(
        first.output_dir / "monitoring-metrics.csv"
    )
    assert (first.output_dir / "monitoring-checks.jsonl").exists()
    assert (first.output_dir / "monitoring-alerts.jsonl").exists()
    assert (first.output_dir / "domain-health-summary.csv").exists()
    assert (first.output_dir / "platform-health-summary.csv").exists()
    assert (first.output_dir / "drift-comparison.csv").exists()
    assert (first.report_dir / "lineage.json").exists()
    assert "Monitoring run: monitor-a" in describe_monitoring_report(first.report_dir)
    assert _csv_rows(first.output_dir / "platform-health-summary.csv")[0]["overall_health_status"] == "passed"
    assert _csv_rows(first.output_dir / "domain-health-summary.csv")[5]["monitoring_domain"] == "disruption_scoring"
    assert _csv_rows(first.output_dir / "drift-comparison.csv")[0]["status"] == "skipped"
    assert any(row["status"] in {"passed", "skipped"} for row in _csv_rows(drifted.output_dir / "drift-comparison.csv"))
    assert _normalised_csv(first.output_dir / "monitoring-metrics.csv") == _normalised_csv(
        second.output_dir / "monitoring-metrics.csv"
    )
    assert _normalised_jsonl(first.output_dir / "monitoring-checks.jsonl") == _normalised_jsonl(
        second.output_dir / "monitoring-checks.jsonl"
    )


def test_monitoring_collision_overwrite_and_rejections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("reject-source", "reject-validation", "reject-upstream")
    config = with_overrides(load_monitoring_config(_repo_root() / "configs/monitoring_ci.yaml"), overwrite=False)

    monitor_platform(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        config=config,
        monitoring_run_id="collision",
    )
    with pytest.raises(MonitoringOutputCollisionError):
        monitor_platform(
            generation_run_dir=artefacts["generation_run_dir"],
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=artefacts["disruption_report_dir"],
            config=config,
            monitoring_run_id="collision",
        )
    overwritten = monitor_platform(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        config=with_overrides(config, overwrite=True),
        monitoring_run_id="collision",
    )
    assert overwritten.monitoring_run_id == "collision"

    validation_manifest = artefacts["validation_report_dir"] / "validation-manifest.json"
    original_validation = json.loads(validation_manifest.read_text(encoding="utf-8"))
    failed = {**original_validation, "overall_status": "failed"}
    validation_manifest.write_text(json.dumps(failed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MonitoringSourceError, match="not accepted"):
        monitor_platform(
            validation_report_dir=artefacts["validation_report_dir"], config=config, monitoring_run_id="bad-validation"
        )
    validation_manifest.write_text(json.dumps(original_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    processed_file = Path("data/processed/reject-validation/flight_schedule.csv")
    processed_file.write_text(processed_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(MonitoringIntegrityError, match="Checksum mismatch"):
        monitor_platform(
            validation_report_dir=artefacts["validation_report_dir"], config=config, monitoring_run_id="bad-checksum"
        )
    validate_data(
        source_run_dir=artefacts["generation_run_dir"],
        config=with_validation_overrides(
            load_validation_config(_repo_root() / "configs/validation_ci.yaml"), overwrite=True
        ),
        validation_run_id="reject-validation",
    )

    _build_upstream("other-source", "other-validation", "other-upstream")
    with pytest.raises(MonitoringCompatibilityError, match="does not match"):
        monitor_platform(
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=Path("reports/disruption_scoring/other-upstream"),
            config=config,
            monitoring_run_id="bad-lineage",
        )


def _build_upstream(source_run_id: str, validation_run_id: str, upstream_run_id: str) -> dict[str, Path]:
    generation_config = load_generation_config(_repo_root() / "configs/data_generation_ci.yaml")
    source = generate_data(generation_config, run_id=source_run_id)
    validation_config = load_validation_config(_repo_root() / "configs/validation_ci.yaml")
    validation = validate_data(
        source_run_dir=source.run_dir, config=validation_config, validation_run_id=validation_run_id
    )
    forecast = forecast_passenger_demand(
        validation_report_dir=validation.report_dir,
        config=load_forecasting_config(_repo_root() / "configs/passenger_forecasting_ci.yaml"),
        forecast_run_id=upstream_run_id,
    )
    delay = predict_flight_delays(
        validation_report_dir=validation.report_dir,
        config=load_delay_prediction_config(_repo_root() / "configs/delay_prediction_ci.yaml"),
        delay_run_id=upstream_run_id,
    )
    maintenance = analyse_aircraft_health(
        validation_report_dir=validation.report_dir,
        config=load_maintenance_config(_repo_root() / "configs/maintenance_analytics_ci.yaml"),
        maintenance_run_id=upstream_run_id,
    )
    disruption = score_disruptions(
        validation_report_dir=validation.report_dir,
        config=load_disruption_config(_repo_root() / "configs/disruption_scoring_ci.yaml"),
        disruption_run_id=upstream_run_id,
    )
    return {
        "generation_run_dir": source.run_dir,
        "validation_report_dir": validation.report_dir,
        "forecast_report_dir": forecast.report_dir,
        "delay_report_dir": delay.report_dir,
        "maintenance_report_dir": maintenance.report_dir,
        "disruption_report_dir": disruption.report_dir,
    }


def _csv_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def _normalised_csv(path: Path) -> list[dict[str, str]]:
    rows = _csv_rows(path)
    for row in rows:
        row["monitoring_run_id"] = "<run>"
    return rows


def _normalised_jsonl(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        row["monitoring_run_id"] = "<run>"
        if "monitoring_alert_id" in row:
            row["monitoring_alert_id"] = "<alert>"
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
