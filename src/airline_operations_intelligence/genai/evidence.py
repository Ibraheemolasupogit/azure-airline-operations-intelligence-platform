"""Structured evidence extraction for assistant retrieval."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.genai.contracts import AssistantSource, EvidenceItem

SENSITIVE_TOKENS = ("name", "email", "phone", "address", "passport", "employee")


def extract_evidence(source: AssistantSource, *, redact_sensitive_fields: bool = True) -> list[EvidenceItem]:
    """Extract structured evidence from verified source artefacts."""
    evidence: list[EvidenceItem] = []
    evidence.extend(_validation_evidence(source))
    if "monitoring" in source.optional_manifests:
        evidence.extend(_monitoring_evidence(source))
    if "disruption_scoring" in source.optional_manifests:
        evidence.extend(_disruption_evidence(source))
    if "delay_prediction" in source.optional_manifests:
        evidence.extend(_delay_evidence(source))
    if "passenger_forecasting" in source.optional_manifests:
        evidence.extend(_forecast_evidence(source))
    if "maintenance_analytics" in source.optional_manifests:
        evidence.extend(_maintenance_evidence(source))
    if redact_sensitive_fields:
        evidence = [_redact(item) for item in evidence]
    return sorted(evidence, key=lambda item: item.evidence_id)


def _item(
    *,
    milestone: str,
    domain: str,
    run_id: str | None,
    source_file: str,
    record_id: str | None,
    evidence_type: str,
    entity_type: str | None,
    entity_id: str | None,
    timestamp: str | None,
    metric_name: str | None,
    metric_value: float | str | None,
    severity: str | None,
    summary: str,
    raw_fields: dict[str, Any],
) -> EvidenceItem:
    payload = f"{domain}|{evidence_type}|{record_id}|{entity_type}|{entity_id}|{metric_name}|{summary}"
    return EvidenceItem(
        evidence_id=f"EVD-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12].upper()}",
        source_milestone=milestone,
        source_domain=domain,
        source_run_id=run_id,
        source_file=source_file,
        source_record_id=record_id,
        evidence_type=evidence_type,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_or_date=timestamp,
        metric_name=metric_name,
        metric_value=metric_value,
        severity=severity,
        summary_text=summary,
        raw_fields=dict(sorted(raw_fields.items())),
        checksum_verified=True,
        lineage_verified=True,
        confidence_level="high",
        responsible_use_notes="Synthetic local evidence only; requires human review.",
    )


def _validation_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.validation_manifest
    run_id = source.validation_run_id
    rows = [
        _item(
            milestone="3",
            domain="validation",
            run_id=run_id,
            source_file="validation-manifest.json",
            record_id="validation-summary",
            evidence_type="data_quality_result",
            entity_type="validation_run",
            entity_id=run_id,
            timestamp=manifest.get("completed_at_utc"),
            metric_name="validation_status",
            metric_value=str(manifest.get("overall_status")),
            severity="info",
            summary=(
                f"Validation run {run_id} status {manifest.get('overall_status')} with "
                f"{manifest.get('valid_row_count', 0)} valid rows and "
                f"{manifest.get('quarantined_row_count', 0)} quarantined rows."
            ),
            raw_fields={
                "warning_count": manifest.get("warning_count", 0),
                "error_count": manifest.get("error_count", 0),
                "fatal_count": manifest.get("fatal_count", 0),
            },
        )
    ]
    for dataset in manifest.get("datasets", []):
        rows.append(
            _item(
                milestone="3",
                domain="validation",
                run_id=run_id,
                source_file="validation-manifest.json",
                record_id=str(dataset.get("processed_filename")),
                evidence_type="validation_metric",
                entity_type="dataset",
                entity_id=str(dataset.get("processed_filename")),
                timestamp=manifest.get("completed_at_utc"),
                metric_name="valid_row_count",
                metric_value=float(dataset.get("valid_row_count", 0)),
                severity="info" if dataset.get("error_count", 0) == 0 else "high",
                summary=(
                    f"{dataset.get('processed_filename')} has {dataset.get('valid_row_count', 0)} valid rows, "
                    f"{dataset.get('quarantined_row_count', 0)} quarantined rows, and "
                    f"{dataset.get('error_count', 0)} errors."
                ),
                raw_fields=dataset,
            )
        )
    return rows


def _monitoring_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.optional_manifests["monitoring"]
    run_id = str(manifest.get("monitoring_run_id"))
    rows: list[EvidenceItem] = []
    for metric in manifest.get("metric_values", [])[:60]:
        rows.append(
            _item(
                milestone="8",
                domain="monitoring",
                run_id=run_id,
                source_file="monitoring-manifest.json",
                record_id=str(metric.get("metric_name")),
                evidence_type="monitoring_check",
                entity_type="monitoring_metric",
                entity_id=str(metric.get("monitoring_domain")),
                timestamp=manifest.get("completed_at_utc"),
                metric_name=str(metric.get("metric_name")),
                metric_value=metric.get("metric_value"),
                severity=str(metric.get("severity", "info")),
                summary=f"Monitoring metric {metric.get('metric_name')} is {metric.get('metric_value')}.",
                raw_fields=metric,
            )
        )
    for check in manifest.get("check_summary", [])[:60]:
        rows.append(
            _item(
                milestone="8",
                domain="monitoring",
                run_id=run_id,
                source_file="monitoring-manifest.json",
                record_id=str(check.get("rule_id")),
                evidence_type="monitoring_check",
                entity_type="monitoring_rule",
                entity_id=str(check.get("rule_id")),
                timestamp=check.get("timestamp_generated_utc"),
                metric_name=str(check.get("metric_name")),
                metric_value=check.get("observed_value"),
                severity=str(check.get("severity", "info")),
                summary=f"{check.get('rule_id')} {check.get('status')}: {check.get('message')}",
                raw_fields=check,
            )
        )
    return rows


def _disruption_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.optional_manifests["disruption_scoring"]
    run_id = str(manifest.get("disruption_run_id"))
    output_dir = Path(str(manifest.get("output_dirs", {}).get("outputs", "")))
    rows: list[EvidenceItem] = []
    for row in _csv_rows(output_dir / "disruption_scores.csv"):
        rows.append(
            _item(
                milestone="7",
                domain="disruption_scoring",
                run_id=run_id,
                source_file="disruption_scores.csv",
                record_id=row.get("flight_id"),
                evidence_type="disruption_score",
                entity_type="flight",
                entity_id=row.get("flight_id"),
                timestamp=row.get("scheduled_departure_utc"),
                metric_name="disruption_severity_score",
                metric_value=_float(row.get("disruption_severity_score")),
                severity=row.get("disruption_risk_band"),
                summary=(
                    f"Flight {row.get('flight_id')} on route {row.get('route_id')} has disruption score "
                    f"{row.get('disruption_severity_score')} and risk band {row.get('disruption_risk_band')}."
                ),
                raw_fields=row,
            )
        )
    for row in _csv_rows(output_dir / "route_disruption_summary.csv"):
        rows.append(
            _item(
                milestone="7",
                domain="disruption_scoring",
                run_id=run_id,
                source_file="route_disruption_summary.csv",
                record_id=row.get("route_id"),
                evidence_type="route_summary",
                entity_type="route",
                entity_id=row.get("route_id"),
                timestamp=None,
                metric_name="maximum_disruption_score",
                metric_value=_float(row.get("maximum_disruption_score")),
                severity=row.get("review_priority"),
                summary=(
                    f"Route {row.get('route_id')} has maximum disruption score "
                    f"{row.get('maximum_disruption_score')} with driver {row.get('dominant_disruption_driver')}."
                ),
                raw_fields=row,
            )
        )
    for row in _jsonl_rows(output_dir / "disruption_alerts.jsonl"):
        rows.append(
            _item(
                milestone="7",
                domain="disruption_scoring",
                run_id=run_id,
                source_file="disruption_alerts.jsonl",
                record_id=str(row.get("alert_id")),
                evidence_type="disruption_alert",
                entity_type="flight",
                entity_id=str(row.get("flight_id")),
                timestamp=None,
                metric_name="disruption_severity_score",
                metric_value=row.get("disruption_severity_score"),
                severity=str(row.get("disruption_risk_band")),
                summary=f"Disruption alert {row.get('alert_id')} flags flight {row.get('flight_id')}.",
                raw_fields=row,
            )
        )
    return rows


def _delay_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.optional_manifests["delay_prediction"]
    run_id = str(manifest.get("delay_run_id"))
    output_dir = Path(str(manifest.get("output_dirs", {}).get("predictions", "")))
    return [
        _item(
            milestone="5",
            domain="delay_prediction",
            run_id=run_id,
            source_file="delay_predictions.csv",
            record_id=row.get("flight_id"),
            evidence_type="delay_prediction",
            entity_type="flight",
            entity_id=row.get("flight_id"),
            timestamp=row.get("scheduled_departure_utc"),
            metric_name="delay_probability",
            metric_value=_float(row.get("delay_probability")),
            severity=row.get("risk_band"),
            summary=f"Flight {row.get('flight_id')} has delay probability {row.get('delay_probability')}.",
            raw_fields=row,
        )
        for row in _csv_rows(output_dir / "delay_predictions.csv")
    ]


def _forecast_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.optional_manifests["passenger_forecasting"]
    run_id = str(manifest.get("forecast_run_id"))
    output_dir = Path(str(manifest.get("forecast_output_path", "")))
    return [
        _item(
            milestone="4",
            domain="passenger_forecasting",
            run_id=run_id,
            source_file="passenger_forecast.csv",
            record_id=row.get("flight_id"),
            evidence_type="passenger_forecast",
            entity_type="flight",
            entity_id=row.get("flight_id"),
            timestamp=row.get("operating_date"),
            metric_name="forecast_passengers",
            metric_value=_float(row.get("forecast_passengers")),
            severity="warning" if row.get("constraint_applied") == "True" else "info",
            summary=f"Flight {row.get('flight_id')} forecast passengers {row.get('forecast_passengers')}.",
            raw_fields=row,
        )
        for row in _csv_rows(output_dir / "passenger_forecast.csv")
    ]


def _maintenance_evidence(source: AssistantSource) -> list[EvidenceItem]:
    manifest = source.optional_manifests["maintenance_analytics"]
    run_id = str(manifest.get("maintenance_run_id"))
    output_dir = Path(str(manifest.get("output_dirs", {}).get("outputs", "")))
    rows: list[EvidenceItem] = []
    for row in _jsonl_rows(output_dir / "maintenance_alerts.jsonl"):
        rows.append(
            _item(
                milestone="6",
                domain="maintenance_analytics",
                run_id=run_id,
                source_file="maintenance_alerts.jsonl",
                record_id=str(row.get("alert_id")),
                evidence_type="maintenance_alert",
                entity_type="aircraft",
                entity_id=str(row.get("aircraft_id")),
                timestamp=row.get("event_timestamp_utc"),
                metric_name="aircraft_health_score",
                metric_value=row.get("aircraft_health_score"),
                severity=str(row.get("alert_category")),
                summary=f"Maintenance alert {row.get('alert_id')} applies to aircraft {row.get('aircraft_id')}.",
                raw_fields=row,
            )
        )
    for row in _csv_rows(output_dir / "aircraft_health_summary.csv"):
        rows.append(
            _item(
                milestone="6",
                domain="maintenance_analytics",
                run_id=run_id,
                source_file="aircraft_health_summary.csv",
                record_id=row.get("aircraft_id"),
                evidence_type="aircraft_summary",
                entity_type="aircraft",
                entity_id=row.get("aircraft_id"),
                timestamp=None,
                metric_name="maximum_maintenance_risk_score",
                metric_value=_float(row.get("maximum_maintenance_risk_score")),
                severity=row.get("review_priority"),
                summary=(
                    f"Aircraft {row.get('aircraft_id')} maximum maintenance score "
                    f"{row.get('maximum_maintenance_risk_score')}."
                ),
                raw_fields=row,
            )
        )
    return rows


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return list(csv.DictReader(path.open("r", encoding="utf-8", newline="")))


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _float(raw: object) -> float | None:
    if raw in (None, ""):
        return None
    return float(str(raw))


def _redact(item: EvidenceItem) -> EvidenceItem:
    redacted = {
        key: ("[REDACTED]" if any(token in key.lower() for token in SENSITIVE_TOKENS) else value)
        for key, value in item.raw_fields.items()
    }
    return EvidenceItem(**{**item.__dict__, "raw_fields": redacted})
