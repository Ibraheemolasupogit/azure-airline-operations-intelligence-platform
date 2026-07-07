"""Maintenance analytics summaries and metrics."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow, MaintenanceAlert, MaintenanceScore


def aircraft_summary(maintenance_run_id: str, scores: list[MaintenanceScore]) -> list[dict[str, object]]:
    """Build aircraft-level summary rows."""
    grouped: dict[str, list[MaintenanceScore]] = defaultdict(list)
    for score in scores:
        grouped[score.aircraft_id].append(score)
    rows: list[dict[str, object]] = []
    for aircraft_id, items in sorted(grouped.items()):
        ordered = sorted(items, key=lambda score: score.event_timestamp_utc)
        alert_items = [score for score in items if score.alert_category != "none"]
        rows.append(
            {
                "maintenance_run_id": maintenance_run_id,
                "aircraft_id": aircraft_id,
                "aircraft_type": ordered[-1].aircraft_type,
                "observation_count": len(items),
                "linked_flight_count": len({score.flight_id for score in items if score.flight_id}),
                "latest_event_timestamp_utc": ordered[-1].event_timestamp_utc.isoformat(),
                "average_maintenance_risk_score": sum(score.maintenance_risk_score for score in items) / len(items),
                "maximum_maintenance_risk_score": max(score.maintenance_risk_score for score in items),
                "latest_maintenance_risk_score": ordered[-1].maintenance_risk_score,
                "latest_aircraft_health_score": ordered[-1].aircraft_health_score,
                "alert_count": len(alert_items),
                "highest_alert_category": _highest_alert(score.alert_category for score in items),
                "fault_code_count": sum(1 for score in items if "fault-code evidence" in score.contributing_factors),
                "high_risk_observation_count": sum(1 for score in items if score.risk_band == "high"),
                "review_priority": _review_priority(items),
            }
        )
    return rows


def flight_risk(
    maintenance_run_id: str, rows: list[HealthFeatureRow], scores: list[MaintenanceScore]
) -> list[dict[str, object]]:
    """Build flight-level maintenance-risk summary rows."""
    latest_by_flight: dict[str, tuple[HealthFeatureRow, MaintenanceScore]] = {}
    rows_by_id = {row.health_observation_id: row for row in rows}
    for score in scores:
        if not score.flight_id:
            continue
        row = rows_by_id[score.health_observation_id]
        current = latest_by_flight.get(score.flight_id)
        if current is None or score.event_timestamp_utc > current[1].event_timestamp_utc:
            latest_by_flight[score.flight_id] = (row, score)
    return [
        {
            "maintenance_run_id": maintenance_run_id,
            "flight_id": flight_id,
            "aircraft_id": score.aircraft_id,
            "aircraft_type": score.aircraft_type,
            "scheduled_departure_utc": "",
            "latest_predeparture_telemetry_utc": score.event_timestamp_utc.isoformat(),
            "maintenance_risk_score": score.maintenance_risk_score,
            "aircraft_health_score": score.aircraft_health_score,
            "risk_band": score.risk_band,
            "alert_category": score.alert_category,
            "evidence_count": 1,
            "human_review_required": score.human_review_required,
        }
        for flight_id, (_, score) in sorted(latest_by_flight.items())
    ]


def maintenance_metrics(
    maintenance_run_id: str,
    rows: list[HealthFeatureRow],
    scores: list[MaintenanceScore],
    alerts: list[MaintenanceAlert],
) -> list[dict[str, object]]:
    """Build maintenance metrics rows."""
    total = len(scores)
    high = sum(1 for score in scores if score.risk_band == "high")
    return [
        _metric(
            maintenance_run_id,
            "volume",
            "telemetry_observation_count",
            len(rows),
            len(rows),
            len(rows),
            "passed",
            "",
            "",
        ),
        _metric(
            maintenance_run_id,
            "volume",
            "scored_observation_count",
            total,
            total,
            len(rows),
            "passed" if total == len(rows) else "warning",
            "",
            "Score rows should reconcile to feature rows.",
        ),
        _metric(maintenance_run_id, "alerts", "alert_count", len(alerts), len(alerts), total, "passed", "", ""),
        _metric(
            maintenance_run_id,
            "risk",
            "high_risk_rate",
            0.0 if total == 0 else high / total,
            high,
            total,
            "passed",
            "",
            "Synthetic analytics only.",
        ),
    ]


def distribution(values: list[str]) -> dict[str, int]:
    """Return deterministic distribution."""
    return dict(sorted(Counter(values).items()))


def component_summary(scores: list[MaintenanceScore]) -> dict[str, dict[str, float]]:
    """Summarise component score ranges."""
    names = sorted({name for score in scores for name in score.component_scores})
    return {
        name: {
            "average": sum(score.component_scores[name] for score in scores) / len(scores),
            "maximum": max(score.component_scores[name] for score in scores),
        }
        for name in names
    }


def _metric(
    run_id: str,
    category: str,
    name: str,
    value: float,
    numerator: float,
    denominator: float,
    status: str,
    threshold: str,
    notes: str,
) -> dict[str, object]:
    return {
        "maintenance_run_id": run_id,
        "metric_category": category,
        "metric_name": name,
        "metric_value": value,
        "numerator": numerator,
        "denominator": denominator,
        "status": status,
        "threshold": threshold,
        "notes": notes,
    }


def _highest_alert(categories: Iterable[str]) -> str:
    order = {"none": 0, "advisory": 1, "watch": 2, "action_recommended": 3}
    values = [str(value) for value in categories]
    return max(values, key=lambda value: order.get(value, 0))


def _review_priority(scores: list[MaintenanceScore]) -> str:
    maximum = max(score.maintenance_risk_score for score in scores)
    if maximum >= 0.8:
        return "high"
    if maximum >= 0.6:
        return "medium"
    return "low"
