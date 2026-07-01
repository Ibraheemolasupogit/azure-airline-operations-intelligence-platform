"""Writers for processed and quarantine validation outputs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.validation.models import DatasetContract, DatasetValidationOutput, NormalizedRecord


def write_processed_dataset(output_dir: Path, contract: DatasetContract, records: list[NormalizedRecord]) -> str:
    """Write valid records using the source dataset filename and format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / contract.filename
    if contract.file_format == "csv":
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=contract.field_names)
            writer.writeheader()
            writer.writerows(_ordered_record(record, contract) for record in records)
    else:
        with path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(_ordered_record(record, contract), sort_keys=True, separators=(",", ":")))
                file.write("\n")
    return sha256_file(path)


def write_quarantine_dataset(
    output_dir: Path,
    contract: DatasetContract,
    output: DatasetValidationOutput,
    source_run_id: str,
    validation_run_id: str,
    timestamp_utc: str,
    write_empty: bool,
) -> str | None:
    """Write invalid records with all record-level failure reasons."""
    if not output.quarantined_records and not write_empty:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = contract.filename.replace(".csv", "").replace(".jsonl", "")
    path = output_dir / f"{stem}_quarantine.jsonl"
    failures_by_row = {
        record.row_number: [
            result for result in output.results if result.row_number == record.row_number and not result.passed
        ]
        for record in output.quarantined_records
    }
    with path.open("w", encoding="utf-8") as file:
        for record in output.quarantined_records:
            failures = sorted(failures_by_row[record.row_number], key=lambda result: result.rule_id)
            payload = {
                "source_dataset": output.dataset,
                "source_record": _ordered_record(record, contract),
                "source_row_number": record.row_number,
                "primary_identifier": _primary_identifier(record, contract),
                "failed_rule_ids": [failure.rule_id for failure in failures],
                "severities": sorted({failure.severity for failure in failures}),
                "failure_messages": [failure.message for failure in failures],
                "quarantine_timestamp_utc": timestamp_utc,
                "source_run_id": source_run_id,
                "validation_run_id": validation_run_id,
            }
            file.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            file.write("\n")
    return sha256_file(path)


def write_json(path: Path, payload: object, *, indent: int = 2) -> str:
    """Write deterministic JSON and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=indent, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> str:
    """Write quality metrics CSV and return checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "validation_run_id",
        "dataset",
        "quality_dimension",
        "metric_name",
        "metric_value",
        "numerator",
        "denominator",
        "threshold",
        "status",
        "severity",
        "rule_id",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return sha256_file(path)


def validation_result_dicts(results: object) -> object:
    """Return dataclass validation results as serialisable dictionaries."""
    if isinstance(results, list):
        return [asdict(item) for item in results]
    return results


def _ordered_record(record: NormalizedRecord, contract: DatasetContract) -> dict[str, object]:
    return {field_name: record.data.get(field_name) for field_name in contract.field_names}


def _primary_identifier(record: NormalizedRecord, contract: DatasetContract) -> str:
    return "|".join(
        "" if record.data.get(field) is None else str(record.data.get(field)) for field in contract.primary_key
    )
