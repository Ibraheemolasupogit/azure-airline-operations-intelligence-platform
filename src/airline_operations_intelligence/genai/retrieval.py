"""Deterministic local evidence retrieval."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import GenAIRetrievalError
from airline_operations_intelligence.genai.contracts import EvidenceItem, RetrievalDecision

INTENT_DOMAIN_PRIORITY = {
    "executive_operations_brief": ("monitoring", "disruption_scoring", "validation"),
    "delay_investigation": ("delay_prediction", "disruption_scoring", "monitoring"),
    "disruption_summary": ("disruption_scoring", "monitoring", "delay_prediction"),
    "maintenance_review_brief": ("maintenance_analytics", "monitoring", "disruption_scoring"),
    "forecast_demand_summary": ("passenger_forecasting", "monitoring", "disruption_scoring"),
    "data_quality_brief": ("validation", "monitoring"),
    "monitoring_health_brief": ("monitoring", "validation"),
    "route_risk_brief": ("disruption_scoring", "delay_prediction", "passenger_forecasting", "monitoring"),
    "flight_risk_brief": ("disruption_scoring", "delay_prediction", "passenger_forecasting", "maintenance_analytics"),
}

SEVERITY_SCORE = {
    "critical": 5,
    "severe": 5,
    "high": 4,
    "urgent_review": 4,
    "warning": 3,
    "medium": 2,
    "watch": 2,
    "advisory": 2,
    "low": 1,
    "info": 0,
    None: 0,
}


def retrieve_evidence(
    evidence: list[EvidenceItem],
    *,
    intent: str,
    top_k: int,
    flight_id: str | None = None,
    route_id: str | None = None,
    aircraft_id: str | None = None,
    airport_code: str | None = None,
) -> tuple[list[EvidenceItem], list[RetrievalDecision]]:
    """Retrieve evidence with deterministic ranking."""
    if top_k <= 0:
        raise GenAIRetrievalError("top_k must be positive.")
    ranked = []
    for item in evidence:
        score, reasons = _score(item, intent, flight_id, route_id, aircraft_id, airport_code)
        if score <= 0:
            continue
        ranked.append((score, item.timestamp_or_date or "", item.evidence_id, item, reasons))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    selected = ranked[:top_k]
    decisions = [
        RetrievalDecision(
            evidence_id=item.evidence_id,
            rank=index + 1,
            score=score,
            matched_filters=tuple(reason for reason in reasons if reason.startswith("filter:")),
            ranking_reasons=tuple(reasons),
        )
        for index, (score, _, _, item, reasons) in enumerate(selected)
    ]
    return [item for _, _, _, item, _ in selected], decisions


def _score(
    item: EvidenceItem,
    intent: str,
    flight_id: str | None,
    route_id: str | None,
    aircraft_id: str | None,
    airport_code: str | None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    raw = item.raw_fields
    filters = {
        "flight_id": flight_id,
        "route_id": route_id,
        "aircraft_id": aircraft_id,
        "airport_code": airport_code,
    }
    supplied_filters = {key: value for key, value in filters.items() if value}
    if supplied_filters:
        for key, value in supplied_filters.items():
            if (
                item.entity_id == value
                or raw.get(key) == value
                or raw.get("origin_airport") == value
                or raw.get("destination_airport") == value
            ):
                score += 100
                reasons.append(f"filter:{key}")
        if score < 100:
            return 0.0, []
    priority = INTENT_DOMAIN_PRIORITY.get(intent, ())
    if item.source_domain in priority:
        score += 30 - priority.index(item.source_domain)
        reasons.append(f"domain:{item.source_domain}")
    if intent in {"route_risk_brief", "delay_investigation"} and item.entity_type == "route":
        score += 20
    if intent == "flight_risk_brief" and item.entity_type == "flight":
        score += 20
    severity = str(item.severity).lower() if item.severity is not None else None
    score += SEVERITY_SCORE.get(severity, 0) * 4
    numeric = item.metric_value if isinstance(item.metric_value, int | float) else None
    if numeric is not None:
        score += min(float(numeric), 1.0) * 10 if float(numeric) <= 1 else min(float(numeric) / 100, 1.0) * 10
    if item.source_domain in priority or supplied_filters:
        score += 1
    return score, reasons
