from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    DashboardCompatibilityError,
    DashboardIntegrityError,
    DashboardOutputCollisionError,
    DashboardSourceError,
)
from airline_operations_intelligence.dashboard.config import load_dashboard_config, with_overrides
from airline_operations_intelligence.dashboard.pipeline import build_dashboard_outputs
from airline_operations_intelligence.dashboard.reporting import describe_dashboard_report
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
from airline_operations_intelligence.monitoring.config import load_monitoring_config
from airline_operations_intelligence.monitoring.pipeline import monitor_platform
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.config import with_overrides as with_validation_overrides
from airline_operations_intelligence.validation.pipeline import validate_data


def test_dashboard_outputs_pipeline_evidence_and_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("dash-source", "dash-validation", "dash-upstream")
    config = with_overrides(load_dashboard_config(_repo_root() / "configs/dashboard_outputs_ci.yaml"), overwrite=False)

    first = build_dashboard_outputs(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        passenger_forecast_report_dir=artefacts["forecast_report_dir"],
        delay_prediction_report_dir=artefacts["delay_report_dir"],
        maintenance_report_dir=artefacts["maintenance_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        monitoring_report_dir=artefacts["monitoring_report_dir"],
        config=config,
        dashboard_run_id="dashboard-a",
    )
    second = build_dashboard_outputs(
        generation_run_dir=artefacts["generation_run_dir"],
        validation_report_dir=artefacts["validation_report_dir"],
        passenger_forecast_report_dir=artefacts["forecast_report_dir"],
        delay_prediction_report_dir=artefacts["delay_report_dir"],
        maintenance_report_dir=artefacts["maintenance_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        monitoring_report_dir=artefacts["monitoring_report_dir"],
        config=config,
        dashboard_run_id="dashboard-b",
    )
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))

    assert first.overall_status == "passed"
    assert manifest["row_counts"]["dim_airport"] == 3
    assert manifest["row_counts"]["fact_flight_operations"] == 24
    assert manifest["row_counts"]["fact_passenger_demand"] == 72
    assert manifest["row_counts"]["fact_disruption_score"] == 24
    assert manifest["row_counts"]["fact_monitoring_metric"] == 42
    assert manifest["measure_count"] >= 10
    assert manifest["page_spec_count"] == 8
    assert manifest["input_artefact_checksums_verified"]["validation"]
    assert manifest["input_artefact_checksums_verified"]["disruption_scoring"]
    assert manifest["artefact_checksums"]["fact_flight_operations.csv"] == sha256_file(
        first.output_dir / "fact_flight_operations.csv"
    )
    assert (first.output_dir / "powerbi-semantic-model.json").is_file()
    assert (first.output_dir / "measure-catalogue.json").is_file()
    assert (first.output_dir / "dashboard-page-specs.json").is_file()
    assert (first.output_dir / "dashboard-data-dictionary.json").is_file()
    assert (first.output_dir / "dashboard-quality-results.json").is_file()
    assert (first.report_dir / "lineage.json").is_file()
    assert "Dashboard run: dashboard-a" in describe_dashboard_report(first.report_dir)
    assert _csv_rows(first.output_dir / "dim_route.csv")
    assert _csv_rows(first.output_dir / "kpi_executive_summary.csv")[0]["metric_name"] == "total_flights"
    assert _normalised_csv(first.output_dir / "fact_disruption_score.csv") == _normalised_csv(
        second.output_dir / "fact_disruption_score.csv"
    )
    assert _normalised_json(first.output_dir / "powerbi-semantic-model.json") == _normalised_json(
        second.output_dir / "powerbi-semantic-model.json"
    )

    with pytest.raises(DashboardOutputCollisionError):
        build_dashboard_outputs(
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=artefacts["disruption_report_dir"],
            monitoring_report_dir=artefacts["monitoring_report_dir"],
            config=config,
            dashboard_run_id="dashboard-a",
        )
    overwritten = build_dashboard_outputs(
        validation_report_dir=artefacts["validation_report_dir"],
        disruption_report_dir=artefacts["disruption_report_dir"],
        monitoring_report_dir=artefacts["monitoring_report_dir"],
        config=with_overrides(config, overwrite=True),
        dashboard_run_id="dashboard-a",
    )
    assert overwritten.dashboard_run_id == "dashboard-a"


def test_dashboard_outputs_reject_bad_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("reject-source", "reject-validation", "reject-upstream")
    config = with_overrides(load_dashboard_config(_repo_root() / "configs/dashboard_outputs_ci.yaml"), overwrite=False)

    validation_manifest = artefacts["validation_report_dir"] / "validation-manifest.json"
    original = json.loads(validation_manifest.read_text(encoding="utf-8"))
    validation_manifest.write_text(json.dumps({**original, "overall_status": "failed"}), encoding="utf-8")
    with pytest.raises(DashboardSourceError, match="not accepted"):
        build_dashboard_outputs(
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=artefacts["disruption_report_dir"],
            monitoring_report_dir=artefacts["monitoring_report_dir"],
            config=config,
            dashboard_run_id="bad-validation",
        )
    validation_manifest.write_text(json.dumps(original, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    processed_file = Path("data/processed/reject-validation/flight_schedule.csv")
    processed_file.write_text(processed_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(DashboardIntegrityError, match="Checksum mismatch"):
        build_dashboard_outputs(
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=artefacts["disruption_report_dir"],
            monitoring_report_dir=artefacts["monitoring_report_dir"],
            config=config,
            dashboard_run_id="bad-checksum",
        )
    validate_data(
        source_run_dir=artefacts["generation_run_dir"],
        config=with_validation_overrides(
            load_validation_config(_repo_root() / "configs/validation_ci.yaml"), overwrite=True
        ),
        validation_run_id="reject-validation",
    )

    other = _build_upstream("other-source", "other-validation", "other-upstream")
    with pytest.raises(DashboardCompatibilityError, match="does not match"):
        build_dashboard_outputs(
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=artefacts["disruption_report_dir"],
            monitoring_report_dir=artefacts["monitoring_report_dir"],
            delay_prediction_report_dir=other["delay_report_dir"],
            config=config,
            dashboard_run_id="bad-lineage",
        )


def _build_upstream(source_run_id: str, validation_run_id: str, upstream_run_id: str) -> dict[str, Path]:
    source = generate_data(
        load_generation_config(_repo_root() / "configs/data_generation_ci.yaml"), run_id=source_run_id
    )
    validation = validate_data(
        source_run_dir=source.run_dir,
        config=load_validation_config(_repo_root() / "configs/validation_ci.yaml"),
        validation_run_id=validation_run_id,
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
    monitoring = monitor_platform(
        generation_run_dir=source.run_dir,
        validation_report_dir=validation.report_dir,
        passenger_forecast_report_dir=forecast.report_dir,
        delay_prediction_report_dir=delay.report_dir,
        maintenance_report_dir=maintenance.report_dir,
        disruption_report_dir=disruption.report_dir,
        config=load_monitoring_config(_repo_root() / "configs/monitoring_ci.yaml"),
        monitoring_run_id=upstream_run_id,
    )
    return {
        "generation_run_dir": source.run_dir,
        "validation_report_dir": validation.report_dir,
        "forecast_report_dir": forecast.report_dir,
        "delay_report_dir": delay.report_dir,
        "maintenance_report_dir": maintenance.report_dir,
        "disruption_report_dir": disruption.report_dir,
        "monitoring_report_dir": monitoring.report_dir,
    }


def _csv_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def _normalised_csv(path: Path) -> list[dict[str, str]]:
    rows = _csv_rows(path)
    for row in rows:
        row["dashboard_run_id"] = "<run>"
    return rows


def _normalised_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
