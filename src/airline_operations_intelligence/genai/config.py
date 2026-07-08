"""Configuration parsing for the deterministic operations assistant."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import GenAIAssistantConfigurationError
from airline_operations_intelligence.genai.contracts import SEVERITIES, SUPPORTED_INTENTS

DEFAULT_GENAI_ASSISTANT_CONFIG_PATH = Path("configs/genai_assistant.yaml")
SUPPORTED_RESPONSE_MODES = {"deterministic_template"}


@dataclass(frozen=True)
class AssistantSettings:
    """Validated assistant settings."""

    output_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    assistant_name: str
    response_mode: str
    maximum_context_records: int
    maximum_evidence_references: int
    maximum_response_sections: int
    require_evidence_for_claims: bool
    include_limitations: bool
    include_human_review_statement: bool
    include_synthetic_data_warning: bool
    redact_sensitive_fields: bool
    supported_intents: tuple[str, ...]
    retrieval: dict[str, bool | int]
    guardrails: dict[str, bool | int]
    severity_policy: dict[str, int]


@dataclass(frozen=True)
class GenAIAssistantConfig:
    """Top-level assistant configuration."""

    settings: AssistantSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "genai_assistant": {
                "output_root": s.output_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "assistant_name": s.assistant_name,
                "response_mode": s.response_mode,
                "maximum_context_records": s.maximum_context_records,
                "maximum_evidence_references": s.maximum_evidence_references,
                "maximum_response_sections": s.maximum_response_sections,
                "require_evidence_for_claims": s.require_evidence_for_claims,
                "include_limitations": s.include_limitations,
                "include_human_review_statement": s.include_human_review_statement,
                "include_synthetic_data_warning": s.include_synthetic_data_warning,
                "redact_sensitive_fields": s.redact_sensitive_fields,
                "supported_intents": list(s.supported_intents),
            },
            "retrieval": dict(sorted(s.retrieval.items())),
            "guardrails": dict(sorted(s.guardrails.items())),
            "severity_policy": dict(sorted(s.severity_policy.items())),
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_genai_assistant_config(path: Path | str) -> GenAIAssistantConfig:
    """Load assistant configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise GenAIAssistantConfigurationError(f"GenAI assistant configuration not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GenAIAssistantConfigurationError(f"GenAI assistant YAML is invalid: {config_path}") from exc
    if not isinstance(raw, dict):
        raise GenAIAssistantConfigurationError("GenAI assistant configuration root must be a mapping.")
    return parse_genai_assistant_config(raw)


def parse_genai_assistant_config(raw: dict[str, Any]) -> GenAIAssistantConfig:
    """Validate raw assistant configuration."""
    assistant = _section(raw, "genai_assistant")
    intents = tuple(_strings(assistant.get("supported_intents"), "supported_intents"))
    if not intents:
        raise GenAIAssistantConfigurationError("supported_intents must not be empty.")
    _reject_duplicates(intents, "supported intents")
    for intent in intents:
        if intent not in SUPPORTED_INTENTS:
            raise GenAIAssistantConfigurationError(f"Unsupported assistant intent in configuration: {intent}")
    response_mode = _str(assistant.get("response_mode"), "response_mode")
    if response_mode not in SUPPORTED_RESPONSE_MODES:
        raise GenAIAssistantConfigurationError(f"Unsupported response mode: {response_mode}")
    settings = AssistantSettings(
        output_root=_root(assistant.get("output_root"), ("outputs", "genai_assistant")),
        report_root=_root(assistant.get("report_root"), ("reports", "genai_assistant")),
        overwrite=_bool(assistant.get("overwrite"), "overwrite"),
        seed=_non_negative_int(assistant.get("seed"), "seed"),
        assistant_name=_str(assistant.get("assistant_name"), "assistant_name"),
        response_mode=response_mode,
        maximum_context_records=_positive_int(assistant.get("maximum_context_records"), "maximum_context_records"),
        maximum_evidence_references=_positive_int(
            assistant.get("maximum_evidence_references"), "maximum_evidence_references"
        ),
        maximum_response_sections=_positive_int(
            assistant.get("maximum_response_sections"), "maximum_response_sections"
        ),
        require_evidence_for_claims=_bool(assistant.get("require_evidence_for_claims"), "require_evidence_for_claims"),
        include_limitations=_bool(assistant.get("include_limitations"), "include_limitations"),
        include_human_review_statement=_bool(
            assistant.get("include_human_review_statement"), "include_human_review_statement"
        ),
        include_synthetic_data_warning=_bool(
            assistant.get("include_synthetic_data_warning"), "include_synthetic_data_warning"
        ),
        redact_sensitive_fields=_bool(assistant.get("redact_sensitive_fields"), "redact_sensitive_fields"),
        supported_intents=intents,
        retrieval=_retrieval(_section(raw, "retrieval")),
        guardrails=_guardrails(_section(raw, "guardrails")),
        severity_policy=_severity_policy(_section(raw, "severity_policy")),
    )
    return GenAIAssistantConfig(settings=settings)


def with_overrides(
    config: GenAIAssistantConfig,
    *,
    output_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool | None = None,
) -> GenAIAssistantConfig:
    """Return config with CLI overrides applied."""
    s = config.settings
    return GenAIAssistantConfig(
        settings=AssistantSettings(
            **{
                **s.__dict__,
                "output_root": output_root if output_root is not None else s.output_root,
                "report_root": report_root if report_root is not None else s.report_root,
                "seed": seed if seed is not None else s.seed,
                "overwrite": overwrite if overwrite is not None else s.overwrite,
            }
        )
    )


def build_assistant_run_id(
    config: GenAIAssistantConfig,
    intent: str,
    validation_run_id: str,
    optional_run_ids: tuple[str | None, ...],
    entity_filters: dict[str, str | None],
    package_version: str,
    explicit_run_id: str | None = None,
) -> str:
    """Build deterministic assistant run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise GenAIAssistantConfigurationError(
                "assistant_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = (
        f"{intent}|{validation_run_id}|{optional_run_ids}|"
        f"{dict(sorted(entity_filters.items()))}|{package_version}|{config.fingerprint()}"
    )
    return f"assistant-{intent}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _section(raw: object, key: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise GenAIAssistantConfigurationError(f"{key} must be a mapping.")
    value = raw.get(key)
    if not isinstance(value, dict):
        raise GenAIAssistantConfigurationError(f"{key} must be a mapping.")
    return value


def _strings(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise GenAIAssistantConfigurationError(f"{label} must contain non-empty strings.")
    return raw


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise GenAIAssistantConfigurationError(f"Duplicate {label} are not allowed.")


def _str(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise GenAIAssistantConfigurationError(f"{label} must be a non-empty string.")
    return raw


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise GenAIAssistantConfigurationError(f"{label} must be boolean.")
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0:
        raise GenAIAssistantConfigurationError(f"{label} must be a positive integer.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise GenAIAssistantConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    if not isinstance(raw, str) or not raw:
        raise GenAIAssistantConfigurationError(f"{'/'.join(allowed_prefix)} path must be a non-empty string.")
    path = Path(raw)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise GenAIAssistantConfigurationError(f"{raw} must remain under {'/'.join(allowed_prefix)}.")
    return path


def _retrieval(raw: dict[str, Any]) -> dict[str, bool | int]:
    expected = {
        "top_k",
        "require_manifest_verification",
        "include_validation_evidence",
        "include_monitoring_evidence",
        "include_disruption_evidence",
        "include_delay_prediction_evidence",
        "include_maintenance_evidence",
        "include_passenger_forecast_evidence",
    }
    if set(raw) != expected:
        raise GenAIAssistantConfigurationError("retrieval must contain supported keys exactly.")
    parsed: dict[str, bool | int] = {"top_k": _positive_int(raw["top_k"], "retrieval.top_k")}
    for key, value in raw.items():
        if key != "top_k":
            parsed[key] = _bool(value, f"retrieval.{key}")
    return dict(sorted(parsed.items()))


def _guardrails(raw: dict[str, Any]) -> dict[str, bool | int]:
    expected = {
        "reject_unsupported_intents",
        "prohibit_autonomous_operational_actions",
        "prohibit_safety_critical_instructions",
        "prohibit_real_world_claims",
        "prohibit_personal_data",
        "require_grounding",
        "require_disclaimer",
        "maximum_ungrounded_claims",
    }
    if set(raw) != expected:
        raise GenAIAssistantConfigurationError("guardrails must contain supported keys exactly.")
    parsed: dict[str, bool | int] = {
        "maximum_ungrounded_claims": _non_negative_int(
            raw["maximum_ungrounded_claims"], "guardrails.maximum_ungrounded_claims"
        )
    }
    for key, value in raw.items():
        if key != "maximum_ungrounded_claims":
            parsed[key] = _bool(value, f"guardrails.{key}")
    return dict(sorted(parsed.items()))


def _severity_policy(raw: dict[str, Any]) -> dict[str, int]:
    if set(raw) != set(SEVERITIES):
        raise GenAIAssistantConfigurationError("severity_policy must define info, warning, high, and critical.")
    policy = {severity: _non_negative_int(raw[severity], f"severity_policy.{severity}") for severity in SEVERITIES}
    ordered = [policy[severity] for severity in SEVERITIES]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise GenAIAssistantConfigurationError("severity_policy must be strictly increasing.")
    return dict(sorted(policy.items()))
