"""End-to-end governed ingestion and validation pipeline."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from airline_operations_intelligence.common.exceptions import IngestionError, ValidationOutputCollisionError
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.ingestion.discovery import discover_source_run
from airline_operations_intelligence.ingestion.readers import read_source_dataset
from airline_operations_intelligence.validation.config import ValidationConfig, build_validation_run_id
from airline_operations_intelligence.validation.engine import overall_status, severity_counts, validate_source_records
from airline_operations_intelligence.validation.lineage import build_lineage
from airline_operations_intelligence.validation.metrics import build_quality_metrics
from airline_operations_intelligence.validation.models import ValidationRunResult
from airline_operations_intelligence.validation.reporting import (
    build_summary,
    build_validation_manifest,
    build_validation_results,
)
from airline_operations_intelligence.validation.schemas import contracts_by_name
from airline_operations_intelligence.validation.writers import (
    write_json,
    write_metrics_csv,
    write_processed_dataset,
    write_quarantine_dataset,
)


def validate_data(
    *,
    source_run_dir: Path,
    config: ValidationConfig,
    validation_run_id: str | None = None,
) -> ValidationRunResult:
    """Validate a completed Milestone 2 generation run."""
    source_run = discover_source_run(source_run_dir, config)
    resolved_run_id = build_validation_run_id(config, source_run.run_id, validation_run_id)
    final_interim = config.settings.output_interim_root / resolved_run_id
    final_processed = config.settings.output_processed_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_interim = config.settings.output_interim_root / f".{resolved_run_id}.tmp"
    tmp_processed = config.settings.output_processed_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    finals = (final_interim, final_processed, final_report)
    tmps = (tmp_interim, tmp_processed, tmp_report)
    if any(path.exists() for path in finals) and not config.settings.overwrite:
        raise ValidationOutputCollisionError(f"Validation run already exists: {resolved_run_id}. Use --overwrite.")
    for tmp in tmps:
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        for tmp in tmps:
            tmp.mkdir(parents=True, exist_ok=True)
        normalized_dir = tmp_interim / "normalized"
        quarantine_dir = tmp_interim / "quarantine"
        raw_records = {name: read_source_dataset(source_run.datasets[name]) for name in sorted(source_run.datasets)}
        outputs, dataset_results = validate_source_records(source_run, raw_records, config, started)
        counts = severity_counts(outputs, dataset_results)
        status = overall_status(counts, config)
        contracts = contracts_by_name()
        processed_checksums: dict[str, str] = {}
        quarantine_checksums: dict[str, str | None] = {}
        for dataset, output in sorted(outputs.items()):
            processed_checksums[dataset] = write_processed_dataset(
                tmp_processed, contracts[dataset], output.valid_records
            )
            processed_checksums[f"normalized/{dataset}"] = write_processed_dataset(
                normalized_dir, contracts[dataset], output.valid_records
            )
            if config.settings.quarantine_invalid_records:
                quarantine_checksums[dataset] = write_quarantine_dataset(
                    quarantine_dir,
                    contracts[dataset],
                    output,
                    source_run.run_id,
                    resolved_run_id,
                    started,
                    config.settings.write_empty_quarantine_files,
                )
            else:
                quarantine_checksums[dataset] = None
        metrics = build_quality_metrics(
            resolved_run_id,
            outputs,
            dataset_results,
            config.settings.max_invalid_record_rate,
        )
        metrics_checksum = write_metrics_csv(tmp_report / "quality-metrics.csv", metrics)
        lineage = build_lineage(
            validation_run_id=resolved_run_id,
            source_run=source_run,
            validation_configuration_fingerprint=config.fingerprint(),
            processed_dir=final_processed,
            quarantine_dir=final_interim / "quarantine",
            report_dir=final_report,
            rules_applied=_rules_applied(outputs, dataset_results),
            timestamp_utc=started,
            validator_version="0.1.0",
        )
        lineage_checksum = write_json(tmp_report / "lineage.json", lineage, indent=config.settings.json_indent)
        validation_results = build_validation_results(outputs, dataset_results)
        results_checksum = write_json(
            tmp_report / "validation-results.json",
            validation_results,
            indent=config.settings.json_indent,
        )
        completed = _utc_now()
        report_checksums = {
            "quality-metrics.csv": metrics_checksum,
            "lineage.json": lineage_checksum,
            "validation-results.json": results_checksum,
        }
        manifest = build_validation_manifest(
            validation_run_id=resolved_run_id,
            source_run=source_run,
            config=config,
            started_at_utc=started,
            completed_at_utc=completed,
            overall_status=status,
            outputs=outputs,
            dataset_results=dataset_results,
            severity_counts=counts,
            processed_checksums=processed_checksums,
            quarantine_checksums=quarantine_checksums,
            report_checksums=report_checksums,
        )
        write_json(tmp_report / "validation-manifest.json", manifest, indent=config.settings.json_indent)
        summary = build_summary(
            validation_run_id=resolved_run_id,
            source_run_id=source_run.run_id,
            report_dir=final_report,
            processed_dir=final_processed,
            interim_dir=final_interim,
            started_at_utc=started,
            completed_at_utc=completed,
            overall_status=status,
            outputs=outputs,
            severity_counts=counts,
            checksum_verified=config.settings.verify_source_checksums,
        )
        (tmp_report / "validation-summary.md").write_text(summary, encoding="utf-8")
        for final in finals:
            if final.exists():
                shutil.rmtree(final)
        tmp_interim.replace(final_interim)
        tmp_processed.replace(final_processed)
        tmp_report.replace(final_report)
        row_counts = {
            dataset: {
                "source": output.source_count,
                "valid": len(output.valid_records),
                "quarantined": len(output.quarantined_records),
            }
            for dataset, output in sorted(outputs.items())
        }
        return ValidationRunResult(
            validation_run_id=resolved_run_id,
            source_run_id=source_run.run_id,
            interim_dir=final_interim,
            processed_dir=final_processed,
            report_dir=final_report,
            manifest_path=final_report / "validation-manifest.json",
            results_path=final_report / "validation-results.json",
            lineage_path=final_report / "lineage.json",
            metrics_path=final_report / "quality-metrics.csv",
            summary_path=final_report / "validation-summary.md",
            overall_status=status,
            row_counts=row_counts,
            severity_counts=counts,
        )
    except Exception as exc:
        for tmp in tmps:
            if tmp.exists():
                shutil.rmtree(tmp)
        if isinstance(exc, IngestionError):
            raise
        raise


def verify_validation_report_checksums(report_dir: Path) -> None:
    """Verify validation manifest output checksums for reports and processed/quarantine files."""
    import json

    manifest_path = report_dir / "validation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    processed_dir = Path(str(report_dir).replace("reports/validation", "data/processed"))
    interim_dir = Path(str(report_dir).replace("reports/validation", "data/interim"))
    for dataset in manifest["datasets"]:
        processed = processed_dir / dataset["processed_filename"]
        if sha256_file(processed) != dataset["processed_sha256"]:
            raise IngestionError(f"Processed checksum mismatch: {processed}")
        quarantine_sha = dataset.get("quarantine_sha256")
        if quarantine_sha:
            quarantine = interim_dir / "quarantine" / dataset["quarantine_filename"]
            if sha256_file(quarantine) != quarantine_sha:
                raise IngestionError(f"Quarantine checksum mismatch: {quarantine}")


def _rules_applied(outputs: object, dataset_results: object) -> list[str]:
    rules = set()
    if isinstance(outputs, dict):
        for output in outputs.values():
            for result in output.results:
                rules.add(result.rule_id)
    if isinstance(dataset_results, list):
        for result in dataset_results:
            rules.add(result.rule_id)
    return sorted(rules | {"MAN-ROWCOUNT", "SCHEMA", "PK", "BUSINESS", "REL"})


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
