"""Generation summary markdown writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.config import GenerationConfig


def build_summary(config: GenerationConfig, manifest: dict[str, Any], run_dir: Path) -> str:
    """Build a Markdown generation summary from actual run metadata."""
    rows = "\n".join(
        f"| `{dataset['filename']}` | {dataset['row_count']} | `{dataset['sha256'][:12]}...` |"
        for dataset in manifest["datasets"]
    )
    date_range = manifest["configured_date_range"]
    return f"""# Synthetic Data Generation Summary

## Run

- Run ID: `{manifest["run_id"]}`
- Profile: `{manifest["generation_profile"]}`
- Date range: `{date_range["start_date"]}` for {date_range["number_of_days"]} days
- Seed: `{manifest["seed"]}`
- Output path: `{run_dir.as_posix()}`

## Datasets

| Dataset | Rows | SHA-256 prefix |
| --- | ---: | --- |
{rows}

## Reference Dimensions

- Fleet size: {len(config.fleet)}
- Route count: {len(config.routes)}
- Airport count: {len(config.airports)}

## Operational Counts

- Aircraft anomaly/watch/review records: {manifest["anomaly_counts"]["aircraft_health_review_or_watch"]}
- Cancelled flights: {manifest["cancellation_counts"]["cancelled_flights"]}
- Diverted flights: {manifest["diversion_counts"]["diverted_flights"]}
- Crew disruptions: {manifest["disruption_counts"]["crew_disruptions"]}
- Major delay flights: {manifest["disruption_counts"]["major_delay_flights"]}
- Airport events: {manifest["disruption_counts"]["airport_events"]}

## Synthetic-Data Warning

All generated records are fictional synthetic data. They do not represent real passengers,
employees, aircraft defects, airport incidents, or confidential airline operations.

## Known Limitations

- Generation invariants prevent obvious corruption but are not the Milestone 3 validation pipeline.
- Sensor ranges and operational thresholds are illustrative and not certified aviation thresholds.
- Crew operations are synthetic and do not claim legal flight-time-limit compliance.
"""


def write_summary(path: Path, summary: str) -> None:
    """Write a Markdown summary."""
    path.write_text(summary, encoding="utf-8")
