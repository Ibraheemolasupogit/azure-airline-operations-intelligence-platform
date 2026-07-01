"""Quality metric calculation for validation runs."""

from __future__ import annotations

from airline_operations_intelligence.validation.models import DatasetValidationOutput, ValidationResult


def build_quality_metrics(
    validation_run_id: str,
    outputs: dict[str, DatasetValidationOutput],
    dataset_results: list[ValidationResult],
    max_invalid_rate: float,
) -> list[dict[str, object]]:
    """Build deterministic quality metric rows."""
    rows: list[dict[str, object]] = []
    dataset_level_failures = _dataset_failure_counts(dataset_results)
    for dataset, output in sorted(outputs.items()):
        source = output.source_count
        quarantined = len(output.quarantined_records)
        valid = len(output.valid_records)
        invalid_rate = 0.0 if source == 0 else quarantined / source
        error_count = sum(1 for result in output.results if not result.passed and result.severity == "error")
        warning_count = sum(1 for result in output.results if not result.passed and result.severity == "warning")
        rows.extend(
            [
                _row(
                    validation_run_id,
                    dataset,
                    "completeness",
                    "source_rows",
                    source,
                    source,
                    source,
                    "",
                    "passed",
                    "info",
                    "MAN-ROWCOUNT",
                ),
                _row(
                    validation_run_id,
                    dataset,
                    "validity",
                    "valid_rows",
                    valid,
                    valid,
                    source,
                    "",
                    "passed" if error_count == 0 else "failed",
                    "error",
                    "SCHEMA",
                ),
                _row(
                    validation_run_id,
                    dataset,
                    "validity",
                    "quarantined_rows",
                    quarantined,
                    quarantined,
                    source,
                    max_invalid_rate,
                    "passed" if invalid_rate <= max_invalid_rate else "failed",
                    "error",
                    "QUARANTINE",
                ),
                _row(
                    validation_run_id,
                    dataset,
                    "integrity",
                    "dataset_level_failures",
                    dataset_level_failures.get(dataset, 0),
                    dataset_level_failures.get(dataset, 0),
                    1,
                    0,
                    "passed" if dataset_level_failures.get(dataset, 0) == 0 else "failed",
                    "fatal",
                    "MAN",
                ),
                _row(
                    validation_run_id,
                    dataset,
                    "conformity",
                    "warning_count",
                    warning_count,
                    warning_count,
                    source,
                    "",
                    "passed",
                    "warning",
                    "WARN",
                ),
            ]
        )
    return rows


def _dataset_failure_counts(results: list[ValidationResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        if not result.passed:
            counts[result.dataset] = counts.get(result.dataset, 0) + 1
    return counts


def _row(
    validation_run_id: str,
    dataset: str,
    dimension: str,
    metric_name: str,
    metric_value: object,
    numerator: object,
    denominator: object,
    threshold: object,
    status: str,
    severity: str,
    rule_id: str,
) -> dict[str, object]:
    return {
        "validation_run_id": validation_run_id,
        "dataset": dataset,
        "quality_dimension": dimension,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "numerator": numerator,
        "denominator": denominator,
        "threshold": threshold,
        "status": status,
        "severity": severity,
        "rule_id": rule_id,
    }
