"""Leakage checks for disruption scoring."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import DisruptionLeakageDetectedError

FORWARD_COMPONENTS = {
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
RETROSPECTIVE_ONLY = {
    "departure_delay_minutes",
    "arrival_delay_minutes",
    "cancelled_flag",
    "diverted_flag",
    "reactionary_delay_minutes",
}


def assert_forward_risk_inputs(feature_names: set[str]) -> list[str]:
    """Ensure forward-risk feature set excludes actual outcome fields."""
    offenders = sorted((feature_names & RETROSPECTIVE_ONLY) - FORWARD_COMPONENTS)
    if offenders:
        raise DisruptionLeakageDetectedError(
            f"Forward-risk features include retrospective outcomes: {', '.join(offenders)}"
        )
    return ["Forward-risk component excludes actual delay, cancellation, diversion, and reactionary outcome fields."]
