"""End-to-end deterministic operations assistant pipeline."""

from __future__ import annotations

import shutil
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import (
    GenAIAssistantConfigurationError,
    GenAIOutputCollisionError,
)
from airline_operations_intelligence.genai.artefacts import dataclass_payload, write_json, write_jsonl, write_text
from airline_operations_intelligence.genai.config import GenAIAssistantConfig, build_assistant_run_id
from airline_operations_intelligence.genai.contracts import SUPPORTED_INTENTS, AssistantRunResult
from airline_operations_intelligence.genai.discovery import discover_assistant_source
from airline_operations_intelligence.genai.evidence import extract_evidence
from airline_operations_intelligence.genai.guardrails import run_guardrails
from airline_operations_intelligence.genai.lineage import build_lineage
from airline_operations_intelligence.genai.prompts import assemble_prompt
from airline_operations_intelligence.genai.reporting import (
    build_evidence_report,
    build_governance_report,
    build_summary,
    response_markdown,
)
from airline_operations_intelligence.genai.retrieval import retrieve_evidence
from airline_operations_intelligence.genai.templates import generate_response


def run_operations_assistant(
    *,
    validation_report_dir: Path,
    config: GenAIAssistantConfig,
    intent: str,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    disruption_report_dir: Path | None = None,
    monitoring_report_dir: Path | None = None,
    flight_id: str | None = None,
    route_id: str | None = None,
    aircraft_id: str | None = None,
    airport_code: str | None = None,
    assistant_run_id: str | None = None,
) -> AssistantRunResult:
    """Run a deterministic local assistant workflow."""
    if intent not in SUPPORTED_INTENTS or intent not in config.settings.supported_intents:
        raise GenAIAssistantConfigurationError(f"Unsupported assistant intent: {intent}")
    source = discover_assistant_source(
        validation_report_dir=validation_report_dir,
        generation_run_dir=generation_run_dir,
        passenger_forecast_report_dir=passenger_forecast_report_dir,
        delay_prediction_report_dir=delay_prediction_report_dir,
        maintenance_report_dir=maintenance_report_dir,
        disruption_report_dir=disruption_report_dir,
        monitoring_report_dir=monitoring_report_dir,
    )
    optional_ids = tuple(
        _optional_id(domain, manifest) for domain, manifest in sorted(source.optional_manifests.items())
    )
    filters = {
        "flight_id": flight_id,
        "route_id": route_id,
        "aircraft_id": aircraft_id,
        "airport_code": airport_code,
    }
    resolved_run_id = build_assistant_run_id(
        config, intent, source.validation_run_id, optional_ids, filters, __version__, assistant_run_id
    )
    final_output = config.settings.output_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    if any(path.exists() for path in (final_output, final_report)) and not config.settings.overwrite:
        raise GenAIOutputCollisionError(f"Assistant run already exists: {resolved_run_id}. Use --overwrite.")
    for tmp in (tmp_output, tmp_report):
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        tmp_output.mkdir(parents=True, exist_ok=True)
        tmp_report.mkdir(parents=True, exist_ok=True)
        evidence = extract_evidence(source, redact_sensitive_fields=config.settings.redact_sensitive_fields)
        selected, retrieval = retrieve_evidence(
            evidence,
            intent=intent,
            top_k=int(config.settings.retrieval["top_k"]),
            flight_id=flight_id,
            route_id=route_id,
            aircraft_id=aircraft_id,
            airport_code=airport_code,
        )
        user_request = _user_request(intent, filters)
        prompt = assemble_prompt(intent=intent, user_request=user_request, evidence=selected, config=config)
        source_runs = _source_runs(source)
        response = generate_response(intent=intent, evidence=selected, source_runs=source_runs, config=config)
        guardrails = run_guardrails(intent=intent, response=response, evidence=selected, config=config)
        timestamp = _stable_timestamp(config.settings.seed)
        response_payload = _response_payload(
            resolved_run_id, intent, user_request, response, source_runs, guardrails, timestamp
        )
        evidence_payload = [asdict(item) for item in selected]
        prompt_payload = dataclass_payload(prompt)
        guardrail_payload = [asdict(result) for result in guardrails]
        transcript_rows = _transcript(
            resolved_run_id, intent, user_request, response_payload, selected, guardrails, timestamp
        )
        checksums = {
            "assistant-response.md": write_text(
                tmp_output / "assistant-response.md", response_markdown(response_payload)
            ),
            "assistant-response.json": write_json(tmp_output / "assistant-response.json", response_payload),
            "evidence-pack.json": write_json(
                tmp_output / "evidence-pack.json",
                {"evidence": evidence_payload, "retrieval": [asdict(item) for item in retrieval]},
            ),
            "prompt-audit.json": write_json(tmp_output / "prompt-audit.json", prompt_payload),
            "guardrail-results.json": write_json(
                tmp_output / "guardrail-results.json", {"guardrails": guardrail_payload}
            ),
            "assistant-transcript.jsonl": write_jsonl(tmp_output / "assistant-transcript.jsonl", transcript_rows),
        }
        completed = _utc_now()
        manifest = _manifest(
            resolved_run_id,
            intent,
            source,
            config,
            started,
            completed,
            selected,
            evidence,
            retrieval,
            guardrails,
            checksums,
            final_output,
            final_report,
        )
        write_json(tmp_output / "assistant-run-manifest.json", manifest)
        lineage = build_lineage(
            assistant_run_id=resolved_run_id,
            intent=intent,
            source=source,
            evidence=selected,
            retrieval=retrieval,
            artefact_checksums=checksums,
            output_dir=final_output,
            report_dir=final_report,
            config_fingerprint=config.fingerprint(),
            package_version=__version__,
            timestamp_utc=completed,
        )
        checksums["lineage.json"] = write_json(tmp_report / "lineage.json", lineage)
        checksums["assistant-summary.md"] = write_text(tmp_report / "assistant-summary.md", build_summary(manifest))
        checksums["assistant-governance-report.md"] = write_text(
            tmp_report / "assistant-governance-report.md", build_governance_report(manifest)
        )
        checksums["evidence-report.md"] = write_text(
            tmp_report / "evidence-report.md", build_evidence_report(manifest, evidence_payload)
        )
        manifest["artefact_checksums"] = dict(sorted(checksums.items()))
        manifest["output_artefacts"] = sorted(checksums)
        write_json(tmp_output / "assistant-run-manifest.json", manifest)
        write_json(tmp_report / "assistant-run-manifest.json", manifest)
        for final in (final_output, final_report):
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_report.replace(final_report)
        return AssistantRunResult(
            assistant_run_id=resolved_run_id,
            intent=intent,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            report_dir=final_report,
            manifest_path=final_report / "assistant-run-manifest.json",
            overall_status=manifest["overall_status"],
            row_counts={
                "evidence": len(selected),
                "available_evidence": len(evidence),
                "guardrails": len(guardrails),
                "transcript": len(transcript_rows),
            },
        )
    except Exception:
        for tmp in (tmp_output, tmp_report):
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _manifest(
    run_id: str,
    intent: str,
    source: Any,
    config: GenAIAssistantConfig,
    started: str,
    completed: str,
    selected: list[Any],
    all_evidence: list[Any],
    retrieval: list[Any],
    guardrails: list[Any],
    checksums: dict[str, str],
    output_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    guardrail_counts = Counter(result.status for result in guardrails)
    evidence_sources = Counter(item.source_domain for item in selected)
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "assistant_run_id": run_id,
        "assistant_name": config.settings.assistant_name,
        "intent": intent,
        "source_validation_run_id": source.validation_run_id,
        "source_monitoring_run_id": _manifest_id(source.optional_manifests.get("monitoring"), "monitoring_run_id"),
        "source_disruption_run_id": _manifest_id(
            source.optional_manifests.get("disruption_scoring"), "disruption_run_id"
        ),
        "optional_generation_run_id": source.generation_run_id,
        "optional_passenger_forecast_run_id": _manifest_id(
            source.optional_manifests.get("passenger_forecasting"), "forecast_run_id"
        ),
        "optional_delay_prediction_run_id": _manifest_id(
            source.optional_manifests.get("delay_prediction"), "delay_run_id"
        ),
        "optional_maintenance_run_id": _manifest_id(
            source.optional_manifests.get("maintenance_analytics"), "maintenance_run_id"
        ),
        "assistant_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "package_version": __version__,
        "seed": config.settings.seed,
        "response_mode": config.settings.response_mode,
        "local_template_mode": True,
        "input_manifest_checksums": source.input_manifest_checksums,
        "input_artefact_checksums_verified": source.input_artefact_checksums_verified,
        "accepted_inputs": [_input_payload(item) for item in source.accepted_inputs],
        "rejected_inputs": [_input_payload(item) for item in source.rejected_inputs],
        "evidence_count": len(selected),
        "available_evidence_count": len(all_evidence),
        "evidence_sources": dict(sorted(evidence_sources.items())),
        "retrieval_policy": {
            "top_k": config.settings.retrieval["top_k"],
            "ranking": "entity match, severity, score, intent-domain priority, timestamp, evidence ID",
        },
        "retrieval_decisions": [asdict(item) for item in retrieval],
        "prompt_policy": {
            "prompt_audit_written": True,
            "secrets_allowed": False,
            "personal_data_redaction": config.settings.redact_sensitive_fields,
        },
        "guardrail_policy": config.settings.guardrails,
        "guardrail_results_summary": {
            "passed": guardrail_counts["passed"],
            "failed": guardrail_counts["failed"],
            "warning": guardrail_counts["warning"],
            "overall_status": "passed" if guardrail_counts["failed"] == 0 else "failed",
        },
        "output_artefacts": sorted(checksums),
        "artefact_checksums": dict(sorted(checksums.items())),
        "output_dirs": {"outputs": output_dir.as_posix(), "reports": report_dir.as_posix()},
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed" if guardrail_counts["failed"] == 0 else "failed",
        "synthetic_data_declaration": "Assistant responses use fictional synthetic aviation data only.",
        "responsible_use_disclaimer": (
            "Deterministic local decision-support only; not live LLM output or operational authority."
        ),
        "known_limitations": [
            "No live OpenAI, Azure OpenAI, or Azure AI Foundry calls are made.",
            "Responses are deterministic templates over local synthetic evidence.",
            "Synthetic correlations may be unrealistic and require human review.",
        ],
        "milestone_scope": "Milestone 9 GenAI-style operations assistant only.",
    }


def _response_payload(
    run_id: str,
    intent: str,
    user_request: str,
    response: Any,
    source_runs: dict[str, str | None],
    guardrails: list[Any],
    timestamp: str,
) -> dict[str, Any]:
    guardrail_counts = Counter(result.status for result in guardrails)
    return {
        "assistant_run_id": run_id,
        "intent": intent,
        "user_request": user_request,
        "response_title": response.response_title,
        "response_sections": [asdict(section) for section in response.response_sections],
        "source_runs": source_runs,
        "evidence_references": response.evidence_references,
        "guardrail_summary": dict(sorted(guardrail_counts.items())),
        "human_review_required": True,
        "synthetic_data_warning": "Synthetic data only; not real airline operations evidence.",
        "local_template_mode": True,
        "unsupported_claim_count": response.unsupported_claim_count,
        "generated_at_utc": timestamp,
    }


def _transcript(
    run_id: str,
    intent: str,
    user_request: str,
    response_payload: dict[str, Any],
    evidence: list[Any],
    guardrails: list[Any],
    timestamp: str,
) -> list[dict[str, Any]]:
    return [
        {
            "assistant_run_id": run_id,
            "turn_id": "turn-001",
            "role": "user",
            "content": user_request,
            "intent": intent,
            "evidence_ids": [],
            "guardrail_status": "not_applicable",
            "timestamp_generated_utc": timestamp,
        },
        {
            "assistant_run_id": run_id,
            "turn_id": "turn-002",
            "role": "assistant",
            "content": response_payload["response_title"],
            "intent": intent,
            "evidence_ids": [item.evidence_id for item in evidence],
            "guardrail_status": "passed" if all(result.status == "passed" for result in guardrails) else "failed",
            "timestamp_generated_utc": timestamp,
        },
    ]


def _source_runs(source: Any) -> dict[str, str | None]:
    return {
        "generation": source.generation_run_id,
        "validation": source.validation_run_id,
        "passenger_forecasting": _manifest_id(
            source.optional_manifests.get("passenger_forecasting"), "forecast_run_id"
        ),
        "delay_prediction": _manifest_id(source.optional_manifests.get("delay_prediction"), "delay_run_id"),
        "maintenance_analytics": _manifest_id(
            source.optional_manifests.get("maintenance_analytics"), "maintenance_run_id"
        ),
        "disruption_scoring": _manifest_id(source.optional_manifests.get("disruption_scoring"), "disruption_run_id"),
        "monitoring": _manifest_id(source.optional_manifests.get("monitoring"), "monitoring_run_id"),
    }


def _optional_id(domain: str, manifest: dict[str, Any]) -> str | None:
    keys = {
        "delay_prediction": "delay_run_id",
        "disruption_scoring": "disruption_run_id",
        "maintenance_analytics": "maintenance_run_id",
        "monitoring": "monitoring_run_id",
        "passenger_forecasting": "forecast_run_id",
    }
    return _manifest_id(manifest, keys[domain])


def _manifest_id(manifest: dict[str, Any] | None, key: str) -> str | None:
    return str(manifest[key]) if manifest and manifest.get(key) is not None else None


def _input_payload(item: Any) -> dict[str, Any]:
    return {
        **asdict(item),
        "path": item.path.as_posix(),
        "manifest_path": item.manifest_path.as_posix() if item.manifest_path else None,
    }


def _user_request(intent: str, filters: dict[str, str | None]) -> str:
    parts = [f"Run {intent}."]
    for key, value in sorted(filters.items()):
        if value:
            parts.append(f"{key}={value}.")
    return " ".join(parts)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _stable_timestamp(seed: int) -> str:
    return f"2025-02-{seed % 28 + 1:02d}T00:00:00Z"
