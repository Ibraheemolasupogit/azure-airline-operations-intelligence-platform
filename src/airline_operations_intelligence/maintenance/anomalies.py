"""Deterministic statistical anomaly scoring for telemetry."""

from __future__ import annotations

from statistics import median

from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow

ANOMALY_FIELDS = (
    "engine_vibration_max",
    "engine_temperature_max",
    "hydraulic_pressure_psi",
    "oil_pressure_psi",
    "brake_temperature_c",
)


def anomaly_scores(rows: list[HealthFeatureRow]) -> dict[str, float]:
    """Return robust anomaly score by health observation ID."""
    distributions = {field: [_num(row.features[field]) for row in rows] for field in ANOMALY_FIELDS}
    medians = {field: median(values) for field, values in distributions.items()}
    mads = {
        field: median([abs(value - medians[field]) for value in values]) or 1.0
        for field, values in distributions.items()
    }
    scores: dict[str, float] = {}
    for row in rows:
        field_scores = []
        for field in ANOMALY_FIELDS:
            robust_z = abs(_num(row.features[field]) - medians[field]) / mads[field]
            field_scores.append(min(1.0, robust_z / 6.0))
        scores[row.health_observation_id] = round(sum(field_scores) / len(field_scores), 6)
    return scores


def _num(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0
