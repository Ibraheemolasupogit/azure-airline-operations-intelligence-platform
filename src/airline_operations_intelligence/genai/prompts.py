"""Prompt assembly for deterministic local assistant runs."""

from __future__ import annotations

from dataclasses import asdict

from airline_operations_intelligence.genai.config import GenAIAssistantConfig
from airline_operations_intelligence.genai.contracts import EvidenceItem, PromptAudit


def assemble_prompt(
    *,
    intent: str,
    user_request: str,
    evidence: list[EvidenceItem],
    config: GenAIAssistantConfig,
) -> PromptAudit:
    """Create an auditable prompt artefact without calling an LLM."""
    return PromptAudit(
        system_instruction=(
            "You are a deterministic local airline operations assistant simulation. "
            "Use only supplied synthetic evidence and do not claim live LLM execution."
        ),
        responsible_use_constraints=[
            "Use synthetic data only.",
            "Do not issue operational commands.",
            "Require human operational review.",
            "Cite evidence IDs for every substantive finding.",
        ],
        intent=intent,
        user_request=user_request,
        evidence_pack=[asdict(item) for item in evidence[: config.settings.maximum_context_records]],
        required_response_structure=[
            "title",
            "summary",
            "evidence-backed findings",
            "human review actions",
            "limitations",
            "evidence references",
        ],
        prohibited_claims=[
            "live Azure AI Foundry execution",
            "live Azure OpenAI execution",
            "real airline operational status",
            "autonomous cancellation, diversion, rerouting, grounding, rebooking, or reassignment",
        ],
        output_style_constraints=["concise", "grounded", "audit-friendly", "conservative"],
    )
