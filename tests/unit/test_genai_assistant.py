from __future__ import annotations

from airline_operations_intelligence.genai.config import parse_genai_assistant_config
from airline_operations_intelligence.genai.contracts import EvidenceItem
from airline_operations_intelligence.genai.guardrails import run_guardrails
from airline_operations_intelligence.genai.prompts import assemble_prompt
from airline_operations_intelligence.genai.retrieval import retrieve_evidence
from airline_operations_intelligence.genai.templates import generate_response
from tests.unit.test_genai_assistant_config import _raw_config


def test_retrieval_filters_and_ranks_by_route() -> None:
    evidence = [_evidence("route", "LHR-AMS", "high", 0.8), _evidence("route", "AMS-LHR", "low", 0.1)]

    selected, decisions = retrieve_evidence(evidence, intent="route_risk_brief", top_k=3, route_id="LHR-AMS")

    assert [item.entity_id for item in selected] == ["LHR-AMS"]
    assert decisions[0].matched_filters == ("filter:route_id",)


def test_prompt_template_and_guardrails_are_grounded() -> None:
    config = parse_genai_assistant_config(_raw_config())
    evidence = [_evidence("flight", "FLT-1", "severe", 0.9)]

    prompt = assemble_prompt(
        intent="flight_risk_brief",
        user_request="Run flight_risk_brief.",
        evidence=evidence,
        config=config,
    )
    response = generate_response(
        intent="flight_risk_brief",
        evidence=evidence,
        source_runs={"validation": "val-a"},
        config=config,
    )
    guardrails = run_guardrails(intent="flight_risk_brief", response=response, evidence=evidence, config=config)

    assert prompt.evidence_pack[0]["evidence_id"] == "EVD-5"
    assert response.evidence_references == ["EVD-5"]
    assert all(result.status == "passed" for result in guardrails)


def test_insufficient_evidence_response_stays_conservative() -> None:
    config = parse_genai_assistant_config(_raw_config())

    response = generate_response(
        intent="data_quality_brief",
        evidence=[],
        source_runs={"validation": "val-a"},
        config=config,
    )

    assert "not contain enough relevant evidence" in response.response_sections[0].content
    assert response.evidence_references == []


def _evidence(entity_type: str, entity_id: str, severity: str, value: float) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"EVD-{len(entity_id)}",
        source_milestone="7",
        source_domain="disruption_scoring",
        source_run_id="run-a",
        source_file="disruption_scores.csv",
        source_record_id=entity_id,
        evidence_type="disruption_score",
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_or_date="2025-01-01T00:00:00Z",
        metric_name="score",
        metric_value=value,
        severity=severity,
        summary_text=f"{entity_type} {entity_id} score {value}",
        raw_fields={"route_id": entity_id if entity_type == "route" else "LHR-AMS", "flight_id": entity_id},
        checksum_verified=True,
        lineage_verified=True,
        confidence_level="high",
        responsible_use_notes="Synthetic local evidence only.",
    )
