from __future__ import annotations

import copy

import pytest

from airline_operations_intelligence.common.exceptions import GenAIAssistantConfigurationError
from airline_operations_intelligence.genai.config import parse_genai_assistant_config


def test_genai_assistant_config_parses_valid_configuration() -> None:
    config = parse_genai_assistant_config(_raw_config())

    assert config.settings.output_root.as_posix() == "outputs/genai_assistant"
    assert config.settings.response_mode == "deterministic_template"
    assert "executive_operations_brief" in config.settings.supported_intents
    assert len(config.fingerprint()) == 64


def test_genai_assistant_config_rejects_unsupported_response_mode() -> None:
    raw = _raw_config()
    raw["genai_assistant"]["response_mode"] = "live_llm"

    with pytest.raises(GenAIAssistantConfigurationError, match="Unsupported response mode"):
        parse_genai_assistant_config(raw)


def test_genai_assistant_config_rejects_duplicate_intents() -> None:
    raw = _raw_config()
    raw["genai_assistant"]["supported_intents"].append("executive_operations_brief")

    with pytest.raises(GenAIAssistantConfigurationError, match="Duplicate"):
        parse_genai_assistant_config(raw)


def test_genai_assistant_config_rejects_unsafe_paths() -> None:
    raw = _raw_config()
    raw["genai_assistant"]["output_root"] = "/tmp/assistant"

    with pytest.raises(GenAIAssistantConfigurationError, match="must remain under"):
        parse_genai_assistant_config(raw)


def test_genai_assistant_config_rejects_bad_severity_policy() -> None:
    raw = _raw_config()
    raw["severity_policy"]["critical"] = 1

    with pytest.raises(GenAIAssistantConfigurationError, match="strictly increasing"):
        parse_genai_assistant_config(raw)


def _raw_config() -> dict:
    return copy.deepcopy(
        {
            "genai_assistant": {
                "output_root": "outputs/genai_assistant",
                "report_root": "reports/genai_assistant",
                "overwrite": False,
                "seed": 42,
                "assistant_name": "local_airline_operations_assistant",
                "response_mode": "deterministic_template",
                "maximum_context_records": 20,
                "maximum_evidence_references": 12,
                "maximum_response_sections": 8,
                "require_evidence_for_claims": True,
                "include_limitations": True,
                "include_human_review_statement": True,
                "include_synthetic_data_warning": True,
                "redact_sensitive_fields": True,
                "supported_intents": [
                    "executive_operations_brief",
                    "delay_investigation",
                    "disruption_summary",
                    "maintenance_review_brief",
                    "forecast_demand_summary",
                    "data_quality_brief",
                    "monitoring_health_brief",
                    "route_risk_brief",
                    "flight_risk_brief",
                ],
            },
            "retrieval": {
                "top_k": 8,
                "require_manifest_verification": True,
                "include_validation_evidence": True,
                "include_monitoring_evidence": True,
                "include_disruption_evidence": True,
                "include_delay_prediction_evidence": True,
                "include_maintenance_evidence": True,
                "include_passenger_forecast_evidence": True,
            },
            "guardrails": {
                "reject_unsupported_intents": True,
                "prohibit_autonomous_operational_actions": True,
                "prohibit_safety_critical_instructions": True,
                "prohibit_real_world_claims": True,
                "prohibit_personal_data": True,
                "require_grounding": True,
                "require_disclaimer": True,
                "maximum_ungrounded_claims": 0,
            },
            "severity_policy": {"info": 0, "warning": 1, "high": 2, "critical": 3},
        }
    )
