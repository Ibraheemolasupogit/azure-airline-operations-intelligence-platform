"""Leakage checks for flight-delay prediction."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import DelayLeakageDetectedError
from airline_operations_intelligence.delay_prediction.contracts import DelayModelRow, PartitionedDelayRows

FORBIDDEN_TOKENS = (
    "actual",
    "arrival_delay",
    "departure_delay",
    "delay_category",
    "delay_cause",
    "reactionary",
    "taxi_",
    "airborne",
    "cancelled",
    "diverted",
    "weather_impact_score",
    "airport_impact_score",
    "crew_impact_score",
    "aircraft_impact_score",
    "target",
    "evaluation",
    "error",
)


def assert_no_forbidden_features(rows: list[DelayModelRow]) -> list[str]:
    """Raise if engineered feature names look like target or post-cutoff leakage."""
    names = sorted({name for row in rows for name in row.features})
    offenders = [name for name in names if any(token in name.lower() for token in FORBIDDEN_TOKENS)]
    if offenders:
        raise DelayLeakageDetectedError(f"Forbidden delay prediction features detected: {', '.join(offenders)}")
    return [
        "Feature names exclude actual departure/arrival times, delay outcomes, delay causes, "
        "taxi/airborne fields, cancellation/diversion outcomes, post-cutoff telemetry, and evaluation fields."
    ]


def assert_no_flight_crosses_partitions(partitions: PartitionedDelayRows) -> list[str]:
    """Raise if a flight appears in more than one split."""
    memberships: dict[str, str] = {}
    for name, rows in (
        ("train", partitions.train),
        ("validation", partitions.validation),
        ("test", partitions.test),
    ):
        for row in rows:
            previous = memberships.setdefault(row.flight_id, name)
            if previous != name:
                raise DelayLeakageDetectedError(f"Flight {row.flight_id} appears in {previous} and {name}.")
    return ["No flight_id appears in more than one chronological partition."]
