"""Lineage model construction for validation evidence."""

from __future__ import annotations

from pathlib import Path

from airline_operations_intelligence.validation.models import SourceRun


def build_lineage(
    *,
    validation_run_id: str,
    source_run: SourceRun,
    validation_configuration_fingerprint: str,
    processed_dir: Path,
    quarantine_dir: Path,
    report_dir: Path,
    rules_applied: list[str],
    timestamp_utc: str,
    validator_version: str,
) -> dict[str, object]:
    """Build explicit lineage nodes and edges."""
    source_nodes = [
        {
            "id": f"source:{dataset.filename}",
            "type": "raw_source_file",
            "path": dataset.path.as_posix(),
            "sha256": dataset.sha256,
        }
        for dataset in source_run.datasets.values()
    ]
    processed_nodes = [
        {
            "id": f"processed:{name}",
            "type": "processed_dataset",
            "path": (processed_dir / name).as_posix(),
        }
        for name in sorted(source_run.datasets)
    ]
    quarantine_nodes = [
        {
            "id": f"quarantine:{name}",
            "type": "quarantine_dataset",
            "path": (quarantine_dir / f"{name.replace('.csv', '').replace('.jsonl', '')}_quarantine.jsonl").as_posix(),
        }
        for name in sorted(source_run.datasets)
    ]
    report_nodes = [
        {
            "id": "report:validation-manifest",
            "type": "validation_manifest",
            "path": (report_dir / "validation-manifest.json").as_posix(),
        },
        {
            "id": "report:validation-results",
            "type": "validation_results",
            "path": (report_dir / "validation-results.json").as_posix(),
        },
        {
            "id": "report:quality-metrics",
            "type": "quality_metrics",
            "path": (report_dir / "quality-metrics.csv").as_posix(),
        },
        {"id": "report:lineage", "type": "lineage", "path": (report_dir / "lineage.json").as_posix()},
    ]
    return {
        "schema_version": "1.0",
        "validation_run_id": validation_run_id,
        "source_generation_run_id": source_run.run_id,
        "validation_configuration_fingerprint": validation_configuration_fingerprint,
        "validator_version": validator_version,
        "captured_at_utc": timestamp_utc,
        "rules_applied": rules_applied,
        "nodes": [
            {
                "id": f"source-run:{source_run.run_id}",
                "type": "generation_run",
                "path": source_run.run_dir.as_posix(),
                "configuration_fingerprint": source_run.configuration_fingerprint,
            },
            *source_nodes,
            *processed_nodes,
            *quarantine_nodes,
            *report_nodes,
        ],
        "edges": [
            *[
                {"from": f"source:{name}", "to": f"processed:{name}", "relationship": "validated_to"}
                for name in sorted(source_run.datasets)
            ],
            *[
                {"from": f"source:{name}", "to": f"quarantine:{name}", "relationship": "invalid_records_to"}
                for name in sorted(source_run.datasets)
            ],
            {
                "from": f"source-run:{source_run.run_id}",
                "to": "report:validation-manifest",
                "relationship": "evidenced_by",
            },
        ],
        "future_azure_mapping": {
            "source_discovery": "ADLS Gen2 landing-zone discovery",
            "validation_rules": "governed data-quality jobs",
            "processed_outputs": "ADLS curated zone and Synapse analytical layer",
            "quarantine_outputs": "ADLS quarantine zone",
            "lineage": "Microsoft Purview",
        },
    }
