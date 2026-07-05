"""Leakage checks for passenger forecasting."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import LeakageDetectedError
from airline_operations_intelligence.forecasting.contracts import ModelRow, PartitionedRows

FORBIDDEN_FEATURES = {
    "actual_departure_utc",
    "actual_arrival_utc",
    "arrival_delay_minutes",
    "departure_delay_minutes",
    "cancelled_flag",
    "diverted_flag",
    "expected_final_passengers",
    "load_factor",
}


def assert_no_forbidden_features(rows: list[ModelRow]) -> list[str]:
    """Reject features that reveal post-horizon or target information."""
    observed = {name for row in rows for name in row.features}
    forbidden = sorted(observed & FORBIDDEN_FEATURES)
    if forbidden:
        raise LeakageDetectedError(f"Forecasting features leak future or target data: {', '.join(forbidden)}")
    return ["No forbidden target, outcome, or post-departure features are present."]


def assert_no_flight_crosses_partitions(partitions: PartitionedRows) -> list[str]:
    """Ensure all rows for a flight remain in one chronological partition."""
    membership: dict[str, str] = {}
    for partition_name, rows in (
        ("train", partitions.train),
        ("validation", partitions.validation),
        ("test", partitions.test),
    ):
        for row in rows:
            existing = membership.setdefault(row.flight_id, partition_name)
            if existing != partition_name:
                raise LeakageDetectedError(f"Flight {row.flight_id} crosses partitions: {existing}, {partition_name}")
    return ["No flight appears in more than one partition."]
