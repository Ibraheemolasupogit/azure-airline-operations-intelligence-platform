"""Assistant reports and completed-run descriptions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import GenAIArtefactError


def response_markdown(response: dict[str, Any]) -> str:
    """Render assistant response markdown."""
    lines = [f"# {response['response_title']}", "", f"Intent: `{response['intent']}`", ""]
    for section in response["response_sections"]:
        lines.extend([f"## {section['heading']}", "", section["content"], ""])
        if section["evidence_ids"]:
            lines.extend(["Evidence: " + ", ".join(f"`{item}`" for item in section["evidence_ids"]), ""])
    lines.extend(
        [
            "## Evidence References",
            "",
            *[f"- `{item}`" for item in response["evidence_references"]],
            "",
        ]
    )
    return "\n".join(lines)


def build_summary(manifest: dict[str, Any]) -> str:
    """Build assistant summary report."""
    return "\n".join(
        [
            "# Assistant Summary",
            "",
            f"- Assistant run ID: `{manifest['assistant_run_id']}`",
            f"- Intent: `{manifest['intent']}`",
            f"- Source validation run: `{manifest['source_validation_run_id']}`",
            f"- Evidence count: {manifest['evidence_count']}",
            f"- Guardrail status: `{manifest['guardrail_results_summary']['overall_status']}`",
            f"- Response mode: `{manifest['response_mode']}`",
            "",
            manifest["synthetic_data_declaration"],
            manifest["responsible_use_disclaimer"],
            "",
        ]
    )


def build_governance_report(manifest: dict[str, Any]) -> str:
    """Build assistant governance report."""
    return "\n".join(
        [
            "# Assistant Governance Report",
            "",
            "## Intended Use",
            "",
            "Local deterministic GenAI-style decision-support demonstration over synthetic evidence.",
            "",
            "## Out Of Scope",
            "",
            "- Live LLM or Azure AI calls",
            "- Certified operations control",
            "- Safety-critical instructions",
            "- Autonomous cancellation, diversion, rerouting, grounding, rebooking, or reassignment",
            "",
            "## Supported Intents",
            "",
            *[
                f"- `{intent}`"
                for intent in manifest["assistant_configuration"]["genai_assistant"]["supported_intents"]
            ],
            "",
            "## Future Mapping",
            "",
            "- Azure AI Foundry prompt flow or agent workflow",
            "- Azure OpenAI model call replacing local templates",
            "- Azure Monitor or Log Analytics audit telemetry",
            "- Microsoft Purview lineage",
            "- Power BI summaries in Milestone 10",
            "",
            "No live Azure AI or OpenAI service is called in this milestone.",
            "",
        ]
    )


def build_evidence_report(manifest: dict[str, Any], evidence_pack: list[dict[str, Any]]) -> str:
    """Build evidence report."""
    lines = [
        "# Assistant Evidence Report",
        "",
        f"Evidence count: {len(evidence_pack)}",
        "",
        "## Evidence Sources",
        "",
    ]
    for source, count in sorted(manifest["evidence_sources"].items()):
        lines.append(f"- {source}: {count}")
    lines.extend(["", "## Top Evidence", ""])
    for item in evidence_pack[:10]:
        lines.append(f"- `{item['evidence_id']}` {item['source_domain']}: {item['summary_text']}")
    lines.extend(["", "Checksum verification is recorded in the assistant manifest.", ""])
    return "\n".join(lines)


def describe_assistant_report(assistant_report_dir: Path) -> str:
    """Describe a completed assistant run without rerunning."""
    manifest_path = assistant_report_dir / "assistant-run-manifest.json"
    if not manifest_path.exists():
        raise GenAIArtefactError(f"Assistant manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Assistant run: {payload['assistant_run_id']}",
            f"Intent: {payload['intent']}",
            f"Source validation run: {payload['source_validation_run_id']}",
            f"Evidence count: {payload['evidence_count']}",
            f"Guardrails: {payload['guardrail_results_summary']}",
            f"Status: {payload['overall_status']}",
        ]
    )
