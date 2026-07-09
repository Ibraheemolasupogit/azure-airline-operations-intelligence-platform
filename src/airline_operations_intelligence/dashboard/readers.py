"""Source table readers for dashboard transformations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.dashboard.artefacts import read_csv_rows, read_json, read_jsonl
from airline_operations_intelligence.dashboard.contracts import DashboardSource


def load_source_tables(source: DashboardSource) -> dict[str, list[dict[str, Any]]]:
    """Load dashboard source rows from verified source artefacts."""
    processed = source.processed_dir
    tables: dict[str, list[dict[str, Any]]] = {
        "flight_schedule": list(read_csv_rows(processed / "flight_schedule.csv")),
        "delay_history": list(read_csv_rows(processed / "delay_history.csv")),
        "passenger_demand": list(read_csv_rows(processed / "passenger_demand.csv")),
        "aircraft_health": read_jsonl(processed / "aircraft_health.jsonl"),
        "disruption_scores": _csv_optional(source.disruption.output_dir, "disruption_scores.csv"),
        "monitoring_metrics": _csv_optional(source.monitoring.output_dir, "monitoring-metrics.csv"),
        "monitoring_alerts": _jsonl_optional(source.monitoring.output_dir, "monitoring-alerts.jsonl"),
    }
    if "passenger_forecasting" in source.optional:
        tables["passenger_forecast"] = _csv_optional(
            source.optional["passenger_forecasting"].output_dir, "passenger_forecast.csv"
        )
    if "delay_prediction" in source.optional:
        tables["delay_predictions"] = _csv_optional(
            source.optional["delay_prediction"].output_dir, "delay_predictions.csv"
        )
    if "maintenance_analytics" in source.optional:
        tables["maintenance_risk"] = _csv_optional(
            source.optional["maintenance_analytics"].output_dir, "flight_maintenance_risk.csv"
        )
    if "genai_assistant" in source.optional:
        artefact = source.optional["genai_assistant"]
        response = read_json((artefact.output_dir or artefact.report_dir) / "assistant-response.json")
        tables["assistant_response"] = _assistant_rows(response)
    return tables


def _csv_optional(output_dir: Path | None, filename: str) -> list[dict[str, Any]]:
    if output_dir is None:
        return []
    return list(read_csv_rows(output_dir / filename))


def _jsonl_optional(output_dir: Path | None, filename: str) -> list[dict[str, Any]]:
    if output_dir is None:
        return []
    return read_jsonl(output_dir / filename)


def _assistant_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    sections = response.get("response_sections")
    if not isinstance(sections, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        if isinstance(section, dict):
            rows.append(
                {
                    "assistant_run_id": response.get("assistant_run_id", ""),
                    "intent": response.get("intent", ""),
                    "response_title": response.get("response_title", ""),
                    "section_title": section.get("section_title", section.get("title", f"Section {index}")),
                    "section_order": index,
                    "evidence_reference_count": len(response.get("evidence_references", [])),
                    "guardrail_status": response.get("guardrail_summary", {}).get("overall_status", "passed")
                    if isinstance(response.get("guardrail_summary"), dict)
                    else "passed",
                    "human_review_required": response.get("human_review_required", True),
                    "local_template_mode": response.get("local_template_mode", True),
                }
            )
    return rows
