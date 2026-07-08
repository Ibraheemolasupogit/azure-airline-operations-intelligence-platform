"""Deterministic guardrail checks for assistant responses."""

from __future__ import annotations

from airline_operations_intelligence.genai.config import GenAIAssistantConfig
from airline_operations_intelligence.genai.contracts import (
    SUPPORTED_INTENTS,
    AssistantResponse,
    EvidenceItem,
    GuardrailResult,
)

UNSAFE_TERMS = ("cancel the flight", "divert the flight", "ground the aircraft", "rebook passengers")


def run_guardrails(
    *, intent: str, response: AssistantResponse, evidence: list[EvidenceItem], config: GenAIAssistantConfig
) -> list[GuardrailResult]:
    """Run deterministic guardrails and record policy decisions."""
    text = "\n".join(section.content for section in response.response_sections).lower()
    results = [
        _result(
            "GR-INTENT-001",
            "passed" if intent in SUPPORTED_INTENTS and intent in config.settings.supported_intents else "failed",
            "critical",
            "Intent is supported.",
            "Accepted supported intent.",
        ),
        _result(
            "GR-GROUND-001",
            "passed" if _grounded(response, evidence, config) else "failed",
            "critical",
            "Every substantive finding has evidence references.",
            "Checked evidence references.",
        ),
        _result(
            "GR-SAFETY-001",
            "passed" if not any(term in text for term in UNSAFE_TERMS) else "failed",
            "critical",
            "Response avoids autonomous operational instructions.",
            "Unsafe operational terms checked.",
        ),
        _result(
            "GR-SYNTH-001",
            "passed" if "synthetic" in text else "failed",
            "high",
            "Synthetic-data warning is present.",
            "Required synthetic-data wording checked.",
        ),
        _result(
            "GR-LLM-001",
            "passed" if "no live llm" in text else "failed",
            "high",
            "No-live-LLM statement is present.",
            "Required local-template wording checked.",
        ),
        _result(
            "GR-HUMAN-001",
            "passed" if "human" in text and "review" in text else "failed",
            "high",
            "Human review language is present.",
            "Required human-review wording checked.",
        ),
        _result(
            "GR-AZURE-001",
            "passed" if "service was called" in text and "azure ai foundry service was called" in text else "failed",
            "high",
            "Response does not claim live Azure AI execution.",
            "Azure claim wording checked.",
        ),
        _result(
            "GR-PII-001",
            "passed" if "[redacted]" not in text.lower() or config.settings.redact_sensitive_fields else "failed",
            "warning",
            "Personal-looking fields are redacted before prompt and response use.",
            "Redaction policy checked.",
        ),
    ]
    return results


def _grounded(response: AssistantResponse, evidence: list[EvidenceItem], config: GenAIAssistantConfig) -> bool:
    if not config.settings.require_evidence_for_claims:
        return True
    available = {item.evidence_id for item in evidence}
    for section in response.response_sections:
        if section.heading.startswith("Finding") and not (set(section.evidence_ids) & available):
            return False
    return response.unsupported_claim_count <= int(config.settings.guardrails["maximum_ungrounded_claims"])


def _result(guardrail_id: str, status: str, severity: str, message: str, action: str) -> GuardrailResult:
    return GuardrailResult(
        guardrail_id=guardrail_id,
        status=status,
        severity=severity if status != "passed" else "info",
        message=message,
        action_taken=action,
    )
