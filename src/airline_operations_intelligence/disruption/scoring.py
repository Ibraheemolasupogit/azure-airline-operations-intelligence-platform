"""Component scoring for operational disruptions."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import DisruptionScoringError
from airline_operations_intelligence.disruption.config import DisruptionScoringConfig
from airline_operations_intelligence.disruption.contracts import DisruptionFeatureRow, DisruptionScore, ScoreBand
from airline_operations_intelligence.disruption.leakage import assert_forward_risk_inputs

COMPONENT_LABELS = {
    "delay": "delay evidence",
    "weather": "weather impact",
    "airport_events": "airport event impact",
    "crew": "crew readiness",
    "aircraft_health": "aircraft health evidence",
    "passenger_pressure": "passenger pressure",
    "network_reactionary": "network reactionary pressure",
}


def score_disruption_rows(
    rows: list[DisruptionFeatureRow], config: DisruptionScoringConfig
) -> tuple[list[DisruptionScore], list[str]]:
    """Score disruption severity and forward risk for feature rows."""
    if not rows:
        raise DisruptionScoringError("Disruption scoring requires feature rows.")
    leakage_checks = assert_forward_risk_inputs(
        {
            "predicted_delay_probability",
            "predicted_delay_minutes",
            "prior_route_delay_pressure",
            "weather_exposure_flag",
            "airport_event_exposure_flag",
            "captain_available",
            "first_officer_available",
            "crew_shortage_flag",
            "forecast_load_factor",
            "maintenance_risk_score",
            "source_maintenance_risk_score",
        }
    )
    scores: list[DisruptionScore] = []
    for row in rows:
        components = _components(row, config)
        forward = _forward_score(row, components, config)
        retrospective = _retrospective_score(row, components, config)
        severity = _bounded(
            max(
                forward if config.settings.enable_forward_risk_score else 0.0,
                retrospective if config.settings.enable_retrospective_score else 0.0,
            )
        )
        contributing = tuple(
            COMPONENT_LABELS[name]
            for name, value in sorted(components.items(), key=lambda item: (-item[1], item[0]))
            if value > 0
        )
        scores.append(
            DisruptionScore(
                flight_id=row.flight_id,
                route_id=row.route_id,
                operating_date=row.operating_date,
                scheduled_departure_utc=row.scheduled_departure_utc,
                origin_airport=row.origin_airport,
                destination_airport=row.destination_airport,
                aircraft_id=row.aircraft_id,
                component_scores=components,
                forward_disruption_risk_score=round(forward, 6),
                retrospective_disruption_score=round(retrospective, 6),
                disruption_severity_score=round(severity, 6),
                disruption_risk_band=_band(severity, config.settings.risk_bands),
                recovery_priority=_band(severity, config.settings.recovery_priority),
                primary_disruption_driver=contributing[0] if contributing else "no elevated component",
                contributing_factors=contributing,
                recommended_review_action=_action(severity),
                human_review_required=severity >= 0.25,
                optional_passenger_forecast_used=bool(row.features["optional_passenger_forecast_used"]),
                optional_delay_prediction_used=bool(row.features["optional_delay_prediction_used"]),
                optional_maintenance_analytics_used=bool(row.features["optional_maintenance_analytics_used"]),
            )
        )
    return scores, leakage_checks


def _components(row: DisruptionFeatureRow, config: DisruptionScoringConfig) -> dict[str, float]:
    f = row.features
    thresholds = config.settings.thresholds
    delay = max(
        _num(f["predicted_delay_probability"]),
        _num(f["departure_delay_minutes"]) / thresholds["severe_delay_minutes"],
        1.0 if bool(f["cancelled_flag"]) or bool(f["diverted_flag"]) else 0.0,
    )
    weather = max(_num(f["max_weather_impact_score"]), 0.7 if bool(f["severe_weather_flag"]) else 0.0)
    airport = max(
        _num(f["maximum_capacity_reduction_percent"]) / max(1.0, thresholds["high_airport_capacity_reduction"]),
        _num(f["estimated_airport_event_delay"]) / 60.0,
        _num(f["maximum_airport_event_severity"]) / 5.0,
    )
    crew = max(
        1.0 if not bool(f["captain_available"]) or not bool(f["first_officer_available"]) else 0.0,
        0.8 if bool(f["crew_shortage_flag"]) else 0.0,
        0.5 if bool(f["reserve_crew_used"]) else 0.0,
        _num(f["connection_risk_minutes"]) / max(1.0, thresholds["high_crew_connection_risk_minutes"]),
        0.7 if bool(f["crew_disruption_flag"]) else 0.0,
    )
    aircraft = max(
        _num(f["source_maintenance_risk_score"]),
        _num(f["maintenance_risk_score"]),
        1.0 - _num(f["aircraft_health_score"]) if bool(f["optional_maintenance_analytics_used"]) else 0.0,
    )
    passenger = max(
        _num(f["latest_booking_load_factor"]) / max(0.01, thresholds["high_load_factor"]),
        _num(f["forecast_load_factor"]) / max(0.01, thresholds["high_load_factor"]),
        _num(f["demand_uncertainty_width"]) / max(1.0, _num(f["seat_capacity"])),
    )
    network = max(
        _num(f["reactionary_delay_minutes"]) / max(1.0, thresholds["high_reactionary_delay_minutes"]),
        _num(f["prior_route_delay_pressure"]),
        _num(f["same_day_route_disruption_count"]) / 4.0,
    )
    return {
        "delay": _bounded(delay),
        "weather": _bounded(weather),
        "airport_events": _bounded(airport),
        "crew": _bounded(crew),
        "aircraft_health": _bounded(aircraft),
        "passenger_pressure": _bounded(passenger),
        "network_reactionary": _bounded(network),
    }


def _forward_score(row: DisruptionFeatureRow, components: dict[str, float], config: DisruptionScoringConfig) -> float:
    forward_components = {
        **components,
        "delay": max(
            _num(row.features["predicted_delay_probability"]), _num(row.features["prior_route_delay_pressure"])
        ),
        "network_reactionary": _num(row.features["prior_route_delay_pressure"]),
    }
    return _weighted(forward_components, config)


def _retrospective_score(
    row: DisruptionFeatureRow, components: dict[str, float], config: DisruptionScoringConfig
) -> float:
    return _weighted(components, config)


def _weighted(components: dict[str, float], config: DisruptionScoringConfig) -> float:
    return _bounded(
        sum(components[name] * config.settings.component_weights[name] for name in config.settings.component_weights)
    )


def _band(score: float, bands: tuple[ScoreBand, ...]) -> str:
    for band in bands:
        if band.minimum_score <= score <= band.maximum_score:
            return band.name
    return list(bands)[-1].name


def _action(score: float) -> str:
    if score >= 0.75:
        return "Prioritise human operational review; do not treat as autonomous recovery instruction."
    if score >= 0.5:
        return "Review operational evidence and passenger-care implications."
    if score >= 0.25:
        return "Assess crew, aircraft, weather, airport, and passenger evidence."
    return "Monitor synthetic disruption evidence."


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
