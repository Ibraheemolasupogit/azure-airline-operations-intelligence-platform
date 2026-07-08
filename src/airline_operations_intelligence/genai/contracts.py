"""Typed contracts for the deterministic operations assistant."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_INTENTS = (
    "executive_operations_brief",
    "delay_investigation",
    "disruption_summary",
    "maintenance_review_brief",
    "forecast_demand_summary",
    "data_quality_brief",
    "monitoring_health_brief",
    "route_risk_brief",
    "flight_risk_brief",
)

SEVERITIES = ("info", "warning", "high", "critical")


@dataclass(frozen=True)
class AssistantInput:
    """Accepted or rejected assistant input evidence."""

    domain: str
    run_id: str | None
    path: Path
    manifest_path: Path | None
    manifest_sha256: str | None
    accepted: bool
    reason: str


@dataclass(frozen=True)
class AssistantSource:
    """Verified source artefacts for an assistant run."""

    validation_run_id: str
    validation_report_dir: Path
    validation_manifest_path: Path
    validation_manifest: dict[str, Any]
    generation_run_id: str | None
    generation_run_dir: Path | None
    generation_manifest: dict[str, Any] | None
    optional_manifests: dict[str, dict[str, Any]]
    optional_report_dirs: dict[str, Path]
    accepted_inputs: list[AssistantInput]
    rejected_inputs: list[AssistantInput]
    input_manifest_checksums: dict[str, str]
    input_artefact_checksums_verified: dict[str, bool]


@dataclass(frozen=True)
class EvidenceItem:
    """Structured evidence item available to the assistant."""

    evidence_id: str
    source_milestone: str
    source_domain: str
    source_run_id: str | None
    source_file: str
    source_record_id: str | None
    evidence_type: str
    entity_type: str | None
    entity_id: str | None
    timestamp_or_date: str | None
    metric_name: str | None
    metric_value: float | str | None
    severity: str | None
    summary_text: str
    raw_fields: dict[str, Any]
    checksum_verified: bool
    lineage_verified: bool
    confidence_level: str
    responsible_use_notes: str


@dataclass(frozen=True)
class RetrievalDecision:
    """Audit record for evidence retrieval."""

    evidence_id: str
    rank: int
    score: float
    matched_filters: tuple[str, ...]
    ranking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class PromptAudit:
    """Assembled prompt artefact."""

    system_instruction: str
    responsible_use_constraints: list[str]
    intent: str
    user_request: str
    evidence_pack: list[dict[str, Any]]
    required_response_structure: list[str]
    prohibited_claims: list[str]
    output_style_constraints: list[str]


@dataclass(frozen=True)
class ResponseSection:
    """Assistant response section."""

    heading: str
    content: str
    evidence_ids: list[str]


@dataclass(frozen=True)
class AssistantResponse:
    """Deterministic assistant response."""

    response_title: str
    response_sections: list[ResponseSection]
    evidence_references: list[str]
    unsupported_claim_count: int


@dataclass(frozen=True)
class GuardrailResult:
    """Single guardrail result."""

    guardrail_id: str
    status: str
    severity: str
    message: str
    action_taken: str
    evidence_id: str | None = None


@dataclass(frozen=True)
class AssistantRunResult:
    """Result returned by the assistant pipeline."""

    assistant_run_id: str
    intent: str
    source_validation_run_id: str
    output_dir: Path
    report_dir: Path
    manifest_path: Path
    overall_status: str
    row_counts: dict[str, int]
