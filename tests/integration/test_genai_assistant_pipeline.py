from __future__ import annotations

import json
from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import (
    GenAIAssistantCompatibilityError,
    GenAIAssistantConfigurationError,
    GenAIOutputCollisionError,
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
from airline_operations_intelligence.genai.config import load_genai_assistant_config, with_overrides
from airline_operations_intelligence.genai.pipeline import run_operations_assistant
from airline_operations_intelligence.genai.reporting import describe_assistant_report
from airline_operations_intelligence.maintenance.config import load_maintenance_config
from airline_operations_intelligence.maintenance.pipeline import analyse_aircraft_health
from airline_operations_intelligence.monitoring.config import load_monitoring_config
from airline_operations_intelligence.monitoring.pipeline import monitor_platform
from airline_operations_intelligence.validation.config import load_validation_config
from airline_operations_intelligence.validation.pipeline import validate_data


def test_genai_assistant_pipeline_outputs_entity_intent_and_determinism(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("assistant-source", "assistant-validation", "assistant-upstream")
    config = load_genai_assistant_config(_repo_root() / "configs/genai_assistant_ci.yaml")

    first = run_operations_assistant(
        **artefacts,
        config=config,
        intent="executive_operations_brief",
        assistant_run_id="assistant-a",
    )
    second = run_operations_assistant(
        **artefacts,
        config=config,
        intent="executive_operations_brief",
        assistant_run_id="assistant-b",
    )
    route = run_operations_assistant(
        **artefacts,
        config=config,
        intent="route_risk_brief",
        route_id="AMS-LHR",
        assistant_run_id="assistant-route",
    )

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    response = json.loads((first.output_dir / "assistant-response.json").read_text(encoding="utf-8"))
    evidence = json.loads((first.output_dir / "evidence-pack.json").read_text(encoding="utf-8"))
    guardrails = json.loads((first.output_dir / "guardrail-results.json").read_text(encoding="utf-8"))
    assert first.overall_status == "passed"
    assert first.row_counts["evidence"] == 8
    assert response["evidence_references"]
    assert evidence["evidence"]
    assert all(result["status"] == "passed" for result in guardrails["guardrails"])
    assert (first.output_dir / "prompt-audit.json").exists()
    assert (first.output_dir / "assistant-transcript.jsonl").exists()
    assert (first.report_dir / "lineage.json").exists()
    assert "Assistant run: assistant-a" in describe_assistant_report(first.report_dir)
    assert manifest["artefact_checksums"]["assistant-response.json"] == sha256_file(
        first.output_dir / "assistant-response.json"
    )
    assert manifest["input_artefact_checksums_verified"]["monitoring"]
    assert route.intent == "route_risk_brief"
    assert _normalised_response(first.output_dir / "assistant-response.json") == _normalised_response(
        second.output_dir / "assistant-response.json"
    )


def test_genai_assistant_rejections_collision_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    artefacts = _build_upstream("reject-assistant-source", "reject-assistant-validation", "reject-assistant-upstream")
    config = with_overrides(
        load_genai_assistant_config(_repo_root() / "configs/genai_assistant_ci.yaml"), overwrite=False
    )

    run_operations_assistant(
        **artefacts,
        config=config,
        intent="executive_operations_brief",
        assistant_run_id="collision",
    )
    with pytest.raises(GenAIOutputCollisionError):
        run_operations_assistant(
            **artefacts,
            config=config,
            intent="executive_operations_brief",
            assistant_run_id="collision",
        )
    overwritten = run_operations_assistant(
        **artefacts,
        config=with_overrides(config, overwrite=True),
        intent="executive_operations_brief",
        assistant_run_id="collision",
    )
    assert overwritten.assistant_run_id == "collision"

    with pytest.raises(GenAIAssistantConfigurationError, match="Unsupported assistant intent"):
        run_operations_assistant(
            **artefacts,
            config=config,
            intent="unsupported_intent",
            assistant_run_id="unsupported",
        )

    other = _build_upstream("other-assistant-source", "other-assistant-validation", "other-assistant-upstream")
    with pytest.raises(GenAIAssistantCompatibilityError, match="does not match"):
        run_operations_assistant(
            generation_run_dir=None,
            validation_report_dir=artefacts["validation_report_dir"],
            disruption_report_dir=other["disruption_report_dir"],
            config=config,
            intent="disruption_summary",
            assistant_run_id="bad-lineage",
        )


def _build_upstream(source_run_id: str, validation_run_id: str, upstream_run_id: str) -> dict:
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
        "passenger_forecast_report_dir": forecast.report_dir,
        "delay_prediction_report_dir": delay.report_dir,
        "maintenance_report_dir": maintenance.report_dir,
        "disruption_report_dir": disruption.report_dir,
        "monitoring_report_dir": monitoring.report_dir,
    }


def _normalised_response(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["assistant_run_id"] = "<run>"
    return payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
