"""Chronological splitting for flight-delay prediction."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import DelayClassDistributionError, DelayInsufficientDataError
from airline_operations_intelligence.delay_prediction.config import DelayPredictionConfig
from airline_operations_intelligence.delay_prediction.contracts import DelayModelRow, PartitionedDelayRows


def chronological_split(rows: list[DelayModelRow], config: DelayPredictionConfig) -> PartitionedDelayRows:
    """Split rows into deterministic chronological train/validation/test partitions."""
    ordered = sorted(rows, key=lambda row: (row.scheduled_departure_utc, row.flight_id))
    if len(ordered) < config.settings.minimum_training_rows:
        raise DelayInsufficientDataError("Not enough delay prediction rows for configured minimum_training_rows.")
    positives = sum(row.target for row in ordered)
    negatives = len(ordered) - positives
    if positives < config.settings.minimum_positive_rows or negatives < config.settings.minimum_negative_rows:
        raise DelayClassDistributionError("Delay target does not contain the configured minimum class distribution.")
    train_end = max(config.settings.minimum_train_rows, int(len(ordered) * config.settings.train_fraction))
    validation_end = train_end + max(
        config.settings.minimum_validation_rows,
        int(len(ordered) * config.settings.validation_fraction),
    )
    if len(ordered) - validation_end < config.settings.minimum_test_rows:
        validation_end = len(ordered) - config.settings.minimum_test_rows
    if validation_end <= train_end or validation_end >= len(ordered):
        raise DelayInsufficientDataError("Chronological split could not satisfy minimum partition sizes.")
    train = ordered[:train_end]
    validation = ordered[train_end:validation_end]
    test = ordered[validation_end:]
    return PartitionedDelayRows(
        train=train,
        validation=validation,
        test=test,
        boundaries={
            "train_start": train[0].scheduled_departure_utc.isoformat(),
            "train_end": train[-1].scheduled_departure_utc.isoformat(),
            "validation_start": validation[0].scheduled_departure_utc.isoformat(),
            "validation_end": validation[-1].scheduled_departure_utc.isoformat(),
            "test_start": test[0].scheduled_departure_utc.isoformat(),
            "test_end": test[-1].scheduled_departure_utc.isoformat(),
        },
    )
