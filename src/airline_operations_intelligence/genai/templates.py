"""Deterministic assistant response templates."""

from __future__ import annotations

from collections import Counter

from airline_operations_intelligence.genai.config import GenAIAssistantConfig
from airline_operations_intelligence.genai.contracts import AssistantResponse, EvidenceItem, ResponseSection

INTENT_TITLES = {
    "executive_operations_brief": "Executive Operations Brief",
    "delay_investigation": "Delay Investigation Brief",
    "disruption_summary": "Disruption Summary",
    "maintenance_review_brief": "Maintenance Review Brief",
    "forecast_demand_summary": "Forecast Demand Summary",
    "data_quality_brief": "Data Quality Brief",
    "monitoring_health_brief": "Monitoring Health Brief",
    "route_risk_brief": "Route Risk Brief",
    "flight_risk_brief": "Flight Risk Brief",
}


def generate_response(
    *,
    intent: str,
    evidence: list[EvidenceItem],
    source_runs: dict[str, str | None],
    config: GenAIAssistantConfig,
) -> AssistantResponse:
    """Generate a deterministic local-template response."""
    title = INTENT_TITLES[intent]
    refs = [item.evidence_id for item in evidence[: config.settings.maximum_evidence_references]]
    sections: list[ResponseSection] = []
    if not evidence:
        sections.append(
            ResponseSection(
                "Evidence Availability",
                "The supplied artefacts did not contain enough relevant evidence for this intent.",
                [],
            )
        )
    else:
        sections.append(
            ResponseSection(
                "Operational Summary",
                _summary(intent, evidence, source_runs),
                refs[: min(3, len(refs))],
            )
        )
        sections.extend(_finding_sections(evidence, config.settings.maximum_response_sections - 3))
    sections.append(
        ResponseSection(
            "Human Review Actions",
            (
                "Require human review of the referenced synthetic evidence before any operational interpretation. "
                "Do not use this response to autonomously cancel, delay, divert, reroute, ground, rebook, "
                "or reassign flights."
            ),
            refs[: min(3, len(refs))],
        )
    )
    sections.append(
        ResponseSection(
            "Limitations",
            (
                "This response was generated locally with deterministic templates over synthetic portfolio data. "
                "No live LLM, Azure OpenAI, or Azure AI Foundry service was called."
            ),
            [],
        )
    )
    return AssistantResponse(
        response_title=title,
        response_sections=sections[: config.settings.maximum_response_sections],
        evidence_references=refs,
        unsupported_claim_count=0,
    )


def _summary(intent: str, evidence: list[EvidenceItem], source_runs: dict[str, str | None]) -> str:
    domains = Counter(item.source_domain for item in evidence)
    top = evidence[0]
    return (
        f"{INTENT_TITLES[intent]} uses {len(evidence)} evidence records from "
        f"{', '.join(sorted(domains))}. Highest-ranked evidence is {top.evidence_id}: {top.summary_text} "
        f"Source validation run is {source_runs.get('validation')}."
    )


def _finding_sections(evidence: list[EvidenceItem], limit: int) -> list[ResponseSection]:
    sections: list[ResponseSection] = []
    for index, item in enumerate(evidence[: max(limit, 0)], start=1):
        sections.append(
            ResponseSection(
                f"Finding {index}",
                f"{item.summary_text} Evidence reference: {item.evidence_id}.",
                [item.evidence_id],
            )
        )
    return sections
