"""Manifest and completed-run description helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import GenerationError
from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import WrittenDataset
from airline_operations_intelligence.data_generation.writers import sha256_file


def build_manifest(
    *,
    config: GenerationConfig,
    run_id: str,
    written_datasets: list[WrittenDataset],
    warnings: list[str],
) -> dict[str, Any]:
    """Build a generation manifest from actual written files."""
    dataset_entries: list[dict[str, Any]] = []
    counts = _event_counts(written_datasets)
    for written in written_datasets:
        dataset_entries.append(
            {
                "filename": written.dataset.filename,
                "format": written.dataset.file_format,
                "grain": written.dataset.grain,
                "row_count": written.row_count,
                "field_names": written.dataset.field_names,
                "sha256": written.sha256,
                "minimum_event_time": _format_dt(written.minimum_event_time),
                "maximum_event_time": _format_dt(written.maximum_event_time),
                "primary_key": written.dataset.primary_key,
                "foreign_keys": written.dataset.foreign_keys,
            }
        )
    end_date = config.settings.start_date.toordinal() + config.settings.number_of_days - 1
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "run_id": run_id,
        "generation_profile": config.settings.profile,
        "seed": config.settings.seed,
        "configured_date_range": {
            "start_date": config.settings.start_date.isoformat(),
            "number_of_days": config.settings.number_of_days,
            "end_date": datetime.fromordinal(end_date).date().isoformat(),
        },
        "effective_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "generator_version": __version__,
        "generated_at_utc": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "datasets": dataset_entries,
        "warnings": warnings,
        "anomaly_counts": {"aircraft_health_review_or_watch": counts["aircraft_health_review_or_watch"]},
        "cancellation_counts": {"cancelled_flights": counts["cancelled_flights"]},
        "diversion_counts": {"diverted_flights": counts["diverted_flights"]},
        "disruption_counts": {
            "crew_disruptions": counts["crew_disruptions"],
            "major_delay_flights": counts["major_delay_flights"],
            "airport_events": counts["airport_events"],
        },
        "synthetic_data_declaration": (
            "All generated records are fictional synthetic data and contain no personal data, "
            "real passengers, employees, aircraft defects, or confidential airline operations."
        ),
        "known_limitations": [
            "Generation invariants are not a comprehensive data-quality validation pipeline.",
            "Sensor ranges and operational thresholds are illustrative and not certified aviation thresholds.",
            "Crew operations are synthetic and do not claim legal flight-time-limit compliance.",
        ],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write manifest JSON deterministically except for generated_at_utc value."""
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_manifest(run_dir: Path) -> dict[str, Any]:
    """Load a completed run manifest."""
    manifest_path = run_dir / "generation-manifest.json"
    if not manifest_path.exists():
        raise GenerationError(f"Manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GenerationError(f"Manifest is not a JSON object: {manifest_path}")
    return payload


def describe_manifest(run_dir: Path) -> str:
    """Return a concise human-readable description for a completed run."""
    manifest = load_manifest(run_dir)
    lines = [
        f"Run ID: {manifest['run_id']}",
        f"Profile: {manifest['generation_profile']}",
        f"Seed: {manifest['seed']}",
        "Datasets:",
    ]
    for dataset in manifest["datasets"]:
        checksum = str(dataset["sha256"])[:12]
        lines.append(f"- {dataset['filename']}: {dataset['row_count']} rows, sha256={checksum}...")
    return "\n".join(lines)


def verify_manifest_checksums(run_dir: Path) -> None:
    """Verify that files still match manifest checksums."""
    manifest = load_manifest(run_dir)
    for dataset in manifest["datasets"]:
        path = run_dir / str(dataset["filename"])
        if sha256_file(path) != dataset["sha256"]:
            raise GenerationError(f"Checksum mismatch for {path}")


def _event_counts(written_datasets: list[WrittenDataset]) -> dict[str, int]:
    by_name = {written.dataset.filename: written.dataset for written in written_datasets}
    delay = by_name["delay_history.csv"]
    crew = by_name["crew_operations.csv"]
    health = by_name["aircraft_health.jsonl"]
    airport = by_name["airport_events.jsonl"]
    return {
        "cancelled_flights": sum(1 for row in delay.records if bool(row["cancelled_flag"])),
        "diverted_flights": sum(1 for row in delay.records if bool(row["diverted_flag"])),
        "major_delay_flights": sum(1 for row in delay.records if row["delay_category"] == "major"),
        "crew_disruptions": sum(1 for row in crew.records if bool(row["crew_disruption_flag"])),
        "aircraft_health_review_or_watch": sum(
            1 for row in health.records if row["health_status"] in {"review", "watch"}
        ),
        "airport_events": len(airport.records),
    }


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")
