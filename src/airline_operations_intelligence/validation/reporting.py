"""Validation evidence report builders."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.validation.config import ValidationConfig
from airline_operations_intelligence.validation.models import DatasetValidationOutput, SourceRun, ValidationResult


def build_validation_results(
    outputs: dict[str, DatasetValidationOutput],
    dataset_results: list[ValidationResult],
) -> dict[str, object]:
    """Build structured validation results evidence."""
    failed_results = [asdict(result) for result in dataset_results if not result.passed]
    passed_counts: dict[str, int] = {}
    for dataset, output in sorted(outputs.items()):
        failed_results.extend(asdict(result) for result in output.results if not result.passed)
        passed_counts[dataset] = output.source_count
    return {
        "schema_version": "1.0",
        "result_strategy": "Milestone 3 stores all failed results and aggregates successful record counts.",
        "failed_results": sorted(
            failed_results, key=lambda item: (str(item["dataset"]), str(item["row_number"]), str(item["rule_id"]))
        ),
        "aggregated_successful_record_counts": passed_counts,
    }


def build_validation_manifest(
    *,
    validation_run_id: str,
    source_run: SourceRun,
    config: ValidationConfig,
    started_at_utc: str,
    completed_at_utc: str,
    overall_status: str,
    outputs: dict[str, DatasetValidationOutput],
    dataset_results: list[ValidationResult],
    severity_counts: dict[str, int],
    processed_checksums: dict[str, str],
    quarantine_checksums: dict[str, str | None],
    report_checksums: dict[str, str],
) -> dict[str, Any]:
    """Build validation manifest from actual outputs."""
    dataset_entries = []
    for dataset, output in sorted(outputs.items()):
        failures = [
            result for result in [*dataset_results, *output.results] if result.dataset == dataset and not result.passed
        ]
        dataset_entries.append(
            {
                "source_filename": dataset,
                "source_row_count": output.source_count,
                "valid_row_count": len(output.valid_records),
                "quarantined_row_count": len(output.quarantined_records),
                "warning_count": sum(1 for result in failures if result.severity == "warning"),
                "error_count": sum(1 for result in failures if result.severity == "error"),
                "processed_filename": dataset,
                "processed_sha256": processed_checksums[dataset],
                "quarantine_filename": _quarantine_filename(dataset),
                "quarantine_sha256": quarantine_checksums.get(dataset),
                "rules_executed": _rules_executed_for_dataset(dataset),
                "rules_failed": sorted({result.rule_id for result in failures}),
            }
        )
    source_count = sum(output.source_count for output in outputs.values())
    valid_count = sum(len(output.valid_records) for output in outputs.values())
    quarantined_count = sum(len(output.quarantined_records) for output in outputs.values())
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "validation_run_id": validation_run_id,
        "source_generation_run_id": source_run.run_id,
        "source_generation_manifest_sha256": source_run.manifest_sha256,
        "source_configuration_fingerprint": source_run.configuration_fingerprint,
        "validation_configuration": config.effective_configuration(),
        "validation_configuration_fingerprint": config.fingerprint(),
        "validator_version": __version__,
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "overall_status": overall_status,
        "datasets": dataset_entries,
        "rule_summary": _rule_summary(dataset_entries),
        "severity_summary": severity_counts,
        "source_row_count": source_count,
        "valid_row_count": valid_count,
        "quarantined_row_count": quarantined_count,
        "warning_count": severity_counts.get("warning", 0),
        "error_count": severity_counts.get("error", 0),
        "fatal_count": severity_counts.get("fatal", 0),
        "output_file_checksums": {
            "processed": processed_checksums,
            "quarantine": quarantine_checksums,
            "reports": report_checksums,
        },
        "lineage_references": {"lineage": "lineage.json", "quality_metrics": "quality-metrics.csv"},
        "synthetic_data_declaration": (
            "Validation evidence applies to fictional synthetic data and does not certify real operations."
        ),
        "known_limitations": [
            "Milestone 3 validation is local-first and not an enterprise data-quality certification.",
            "Rules validate synthetic operational plausibility, not aviation regulatory compliance.",
            "Azure services are mapped in documentation only; no cloud resources are deployed.",
        ],
    }


def build_summary(
    *,
    validation_run_id: str,
    source_run_id: str,
    report_dir: Path,
    processed_dir: Path,
    interim_dir: Path,
    started_at_utc: str,
    completed_at_utc: str,
    overall_status: str,
    outputs: dict[str, DatasetValidationOutput],
    severity_counts: dict[str, int],
    checksum_verified: bool,
) -> str:
    """Build a Markdown validation summary from actual run results."""
    rows = "\n".join(
        f"| `{dataset}` | {output.source_count} | {len(output.valid_records)} | {len(output.quarantined_records)} |"
        for dataset, output in sorted(outputs.items())
    )
    return f"""# Validation Summary

## Run

- Validation run ID: `{validation_run_id}`
- Source generation run ID: `{source_run_id}`
- Overall status: `{overall_status}`
- Started: `{started_at_utc}`
- Completed: `{completed_at_utc}`
- Interim path: `{interim_dir.as_posix()}`
- Processed path: `{processed_dir.as_posix()}`
- Report path: `{report_dir.as_posix()}`
- Source checksum verification: `{checksum_verified}`

## Dataset Counts

| Dataset | Source rows | Valid rows | Quarantined rows |
| --- | ---: | ---: | ---: |
{rows}

## Finding Counts

- Warnings: {severity_counts.get("warning", 0)}
- Errors: {severity_counts.get("error", 0)}
- Fatal findings: {severity_counts.get("fatal", 0)}

## Evidence

- Validation manifest: `validation-manifest.json`
- Validation results: `validation-results.json`
- Quality metrics: `quality-metrics.csv`
- Lineage: `lineage.json`

## Limitations

This local validation run checks synthetic aviation data for governed development use. It does
not certify real airline operations, aviation safety thresholds, legal crew compliance, or cloud
production readiness.
"""


def describe_validation_manifest(report_dir: Path) -> str:
    """Return a concise description of a completed validation run."""
    import json

    manifest_path = report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lines = [
        f"Validation run ID: {manifest['validation_run_id']}",
        f"Source generation run ID: {manifest['source_generation_run_id']}",
        f"Overall status: {manifest['overall_status']}",
        "Datasets:",
    ]
    for dataset in manifest["datasets"]:
        lines.append(
            f"- {dataset['source_filename']}: source={dataset['source_row_count']}, "
            f"valid={dataset['valid_row_count']}, quarantined={dataset['quarantined_row_count']}"
        )
    return "\n".join(lines)


def _quarantine_filename(dataset: str) -> str:
    return f"{dataset.replace('.csv', '').replace('.jsonl', '')}_quarantine.jsonl"


def _rules_executed_for_dataset(dataset: str) -> list[str]:
    prefix = {
        "flight_schedule.csv": "FS",
        "passenger_demand.csv": "PD",
        "weather_events.csv": "WE",
        "aircraft_health.jsonl": "AH",
        "crew_operations.csv": "CR",
        "delay_history.csv": "DH",
        "airport_events.jsonl": "AE",
    }[dataset]
    return ["MAN", f"{prefix}-SCHEMA", f"{prefix}-PK", f"{prefix}-BUSINESS", "REL"]


def _rule_summary(dataset_entries: list[dict[str, Any]]) -> dict[str, int]:
    failed_rules = sorted({rule for entry in dataset_entries for rule in entry["rules_failed"]})
    return {"failed_rule_count": len(failed_rules), "dataset_count": len(dataset_entries)}
