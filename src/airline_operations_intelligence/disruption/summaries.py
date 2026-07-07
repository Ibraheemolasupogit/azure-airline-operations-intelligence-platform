"""Summary aggregations for disruption scoring."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from airline_operations_intelligence.disruption.contracts import DisruptionAlert, DisruptionFeatureRow, DisruptionScore


def route_summary(
    run_id: str, scores: list[DisruptionScore], features: list[DisruptionFeatureRow]
) -> list[dict[str, object]]:
    """Build route disruption summary."""
    by_route: dict[str, list[DisruptionScore]] = defaultdict(list)
    for score in scores:
        by_route[score.route_id].append(score)
    features_by_flight = {row.flight_id: row for row in features}
    rows = []
    for route_id, items in sorted(by_route.items()):
        feature_items = [features_by_flight[item.flight_id] for item in items]
        rows.append(
            {
                "disruption_run_id": run_id,
                "route_id": route_id,
                "flight_count": len(items),
                "average_disruption_score": _avg(item.disruption_severity_score for item in items),
                "maximum_disruption_score": max(item.disruption_severity_score for item in items),
                "severe_or_high_count": _severe_high(items),
                "cancellation_count": sum(1 for row in feature_items if bool(row.features["cancelled_flag"])),
                "diversion_count": sum(1 for row in feature_items if bool(row.features["diverted_flag"])),
                "average_delay_minutes": _avg(_num(row.features["departure_delay_minutes"]) for row in feature_items),
                "dominant_disruption_driver": _dominant(item.primary_disruption_driver for item in items),
                "review_priority": _priority(items),
            }
        )
    return rows


def airport_summary(
    run_id: str, scores: list[DisruptionScore], features: list[DisruptionFeatureRow]
) -> list[dict[str, object]]:
    """Build airport disruption summary."""
    airports = sorted({score.origin_airport for score in scores} | {score.destination_airport for score in scores})
    features_by_flight = {row.flight_id: row for row in features}
    rows = []
    for airport in airports:
        departures = [score for score in scores if score.origin_airport == airport]
        arrivals = [score for score in scores if score.destination_airport == airport]
        items = departures + arrivals
        if not items:
            continue
        feature_items = [features_by_flight[item.flight_id] for item in items]
        rows.append(
            {
                "disruption_run_id": run_id,
                "airport_code": airport,
                "departure_flight_count": len(departures),
                "arrival_flight_count": len(arrivals),
                "average_disruption_score": _avg(item.disruption_severity_score for item in items),
                "maximum_disruption_score": max(item.disruption_severity_score for item in items),
                "weather_event_count": sum(
                    _num(row.features["origin_weather_event_count"])
                    + _num(row.features["destination_weather_event_count"])
                    for row in feature_items
                ),
                "airport_event_count": sum(_num(row.features["airport_event_count"]) for row in feature_items),
                "severe_or_high_count": _severe_high(items),
                "dominant_disruption_driver": _dominant(item.primary_disruption_driver for item in items),
                "review_priority": _priority(items),
            }
        )
    return rows


def aircraft_summary(run_id: str, scores: list[DisruptionScore]) -> list[dict[str, object]]:
    """Build aircraft disruption summary."""
    grouped: dict[str, list[DisruptionScore]] = defaultdict(list)
    for score in scores:
        grouped[score.aircraft_id].append(score)
    return [
        {
            "disruption_run_id": run_id,
            "aircraft_id": aircraft_id,
            "aircraft_type": "",
            "flight_count": len(items),
            "average_disruption_score": _avg(item.disruption_severity_score for item in items),
            "maximum_disruption_score": max(item.disruption_severity_score for item in items),
            "maintenance_related_count": sum(1 for item in items if item.component_scores["aircraft_health"] > 0),
            "reactionary_delay_count": sum(1 for item in items if item.component_scores["network_reactionary"] > 0),
            "dominant_disruption_driver": _dominant(item.primary_disruption_driver for item in items),
            "review_priority": _priority(items),
        }
        for aircraft_id, items in sorted(grouped.items())
    ]


def daily_summary(run_id: str, scores: list[DisruptionScore], alerts: list[DisruptionAlert]) -> list[dict[str, object]]:
    """Build daily disruption summary."""
    grouped: dict[str, list[DisruptionScore]] = defaultdict(list)
    alerts_by_date = Counter(alert.operating_date for alert in alerts)
    for score in scores:
        grouped[score.operating_date].append(score)
    return [
        {
            "disruption_run_id": run_id,
            "operating_date": day,
            "flight_count": len(items),
            "average_disruption_score": _avg(item.disruption_severity_score for item in items),
            "maximum_disruption_score": max(item.disruption_severity_score for item in items),
            "severe_or_high_count": _severe_high(items),
            "cancellation_count": 0,
            "diversion_count": 0,
            "alert_count": alerts_by_date[day],
            "dominant_disruption_driver": _dominant(item.primary_disruption_driver for item in items),
            "review_priority": _priority(items),
        }
        for day, items in sorted(grouped.items())
    ]


def disruption_metrics(
    run_id: str, scores: list[DisruptionScore], alerts: list[DisruptionAlert]
) -> list[dict[str, object]]:
    """Build disruption metrics."""
    total = len(scores)
    severe_high = _severe_high(scores)
    return [
        _metric(run_id, "volume", "flight_count", total, total, total, "passed", "", ""),
        _metric(run_id, "alerts", "alert_count", len(alerts), len(alerts), total, "passed", "", ""),
        _metric(
            run_id,
            "risk",
            "high_or_severe_rate",
            0 if total == 0 else severe_high / total,
            severe_high,
            total,
            "passed",
            "",
            "",
        ),
    ]


def distribution(values: list[str]) -> dict[str, int]:
    """Return deterministic distribution."""
    return dict(sorted(Counter(values).items()))


def component_summary(scores: list[DisruptionScore]) -> dict[str, dict[str, float]]:
    """Summarise component scores."""
    names = sorted({name for score in scores for name in score.component_scores})
    return {
        name: {
            "average": _avg(score.component_scores[name] for score in scores),
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
        "disruption_run_id": run_id,
        "metric_category": category,
        "metric_name": name,
        "metric_value": value,
        "numerator": numerator,
        "denominator": denominator,
        "status": status,
        "threshold": threshold,
        "notes": notes,
    }


def _severe_high(items: list[DisruptionScore]) -> int:
    return sum(1 for item in items if item.disruption_risk_band in {"high", "severe"})


def _dominant(values: Iterable[object]) -> str:
    counts = Counter(str(value) for value in values)
    return sorted(counts, key=lambda value: (-counts[value], value))[0]


def _priority(items: list[DisruptionScore]) -> str:
    order = {"monitor": 0, "review": 1, "prioritise": 2, "urgent_review": 3}
    return max((item.recovery_priority for item in items), key=lambda value: order[value])


def _avg(values: Iterable[object]) -> float:
    items = [_num(value) for value in values]
    return 0.0 if not items else sum(items) / len(items)


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
