"""Chronological train, validation, and test splitting."""

from __future__ import annotations

from airline_operations_intelligence.common.exceptions import InsufficientTrainingDataError
from airline_operations_intelligence.forecasting.config import ForecastingConfig
from airline_operations_intelligence.forecasting.contracts import ModelRow, PartitionedRows


def chronological_split(rows: list[ModelRow], config: ForecastingConfig) -> PartitionedRows:
    """Split rows by operating date without randomization."""
    ordered = sorted(rows, key=lambda row: (row.operating_date, row.flight_id, row.observation_id))
    if len(ordered) < 3:
        raise InsufficientTrainingDataError("At least three modelling rows are required for train/validation/test.")
    total = len(ordered)
    train_count = max(config.settings.minimum_train_periods, int(total * config.settings.train_fraction))
    validation_count = max(1, int(total * config.settings.validation_fraction))
    if train_count + validation_count >= total:
        train_count = max(1, total - 2)
        validation_count = 1
    train = ordered[:train_count]
    validation = ordered[train_count : train_count + validation_count]
    test = ordered[train_count + validation_count :]
    if not train or not validation or not test:
        raise InsufficientTrainingDataError("Chronological split produced an empty partition.")
    return PartitionedRows(
        train=train,
        validation=validation,
        test=test,
        boundaries={
            "train_start": train[0].operating_date.isoformat(),
            "train_end": train[-1].operating_date.isoformat(),
            "validation_start": validation[0].operating_date.isoformat(),
            "validation_end": validation[-1].operating_date.isoformat(),
            "test_start": test[0].operating_date.isoformat(),
            "test_end": test[-1].operating_date.isoformat(),
        },
    )
