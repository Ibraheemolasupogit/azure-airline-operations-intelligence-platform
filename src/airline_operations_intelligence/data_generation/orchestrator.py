"""Synthetic data-generation orchestration."""

from __future__ import annotations

import shutil

from airline_operations_intelligence.common.exceptions import OutputCollisionError
from airline_operations_intelligence.data_generation.aircraft_health import generate_aircraft_health
from airline_operations_intelligence.data_generation.airport_events import generate_airport_events
from airline_operations_intelligence.data_generation.config import GenerationConfig, build_run_id
from airline_operations_intelligence.data_generation.crew import generate_crew_operations
from airline_operations_intelligence.data_generation.data_dictionary import (
    build_data_dictionary,
    write_data_dictionary,
)
from airline_operations_intelligence.data_generation.delays import generate_delay_history
from airline_operations_intelligence.data_generation.demand import generate_passenger_demand
from airline_operations_intelligence.data_generation.invariants import check_generation_invariants
from airline_operations_intelligence.data_generation.manifest import build_manifest, write_manifest
from airline_operations_intelligence.data_generation.models import Dataset, GenerationResult
from airline_operations_intelligence.data_generation.randomness import make_rng
from airline_operations_intelligence.data_generation.schedule import generate_schedule
from airline_operations_intelligence.data_generation.summary import build_summary, write_summary
from airline_operations_intelligence.data_generation.weather import generate_weather_events
from airline_operations_intelligence.data_generation.writers import write_dataset


def generate_data(config: GenerationConfig, *, run_id: str | None = None) -> GenerationResult:
    """Generate all Milestone 2 synthetic datasets using atomic output handling."""
    resolved_run_id = build_run_id(config, run_id)
    output_root = config.settings.output_root
    final_dir = output_root / resolved_run_id
    tmp_dir = output_root / f".{resolved_run_id}.tmp"
    if final_dir.exists() and not config.settings.overwrite:
        raise OutputCollisionError(f"Generation run already exists: {final_dir}. Use --overwrite to replace it.")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    try:
        output_root.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True)
        datasets = _generate_datasets(config)
        check_generation_invariants(config, datasets)
        written = [write_dataset(tmp_dir, dataset) for dataset in datasets]
        manifest = build_manifest(
            config=config,
            run_id=resolved_run_id,
            written_datasets=written,
            warnings=["Generation invariants ran, but comprehensive governed validation is deferred to Milestone 3."],
        )
        data_dictionary = build_data_dictionary(datasets)
        manifest_path = tmp_dir / "generation-manifest.json"
        dictionary_path = tmp_dir / "data-dictionary.json"
        summary_path = tmp_dir / "generation-summary.md"
        write_manifest(manifest_path, manifest)
        write_data_dictionary(dictionary_path, data_dictionary)
        write_summary(summary_path, build_summary(config, manifest, final_dir))

        if final_dir.exists():
            shutil.rmtree(final_dir)
        tmp_dir.replace(final_dir)
        return GenerationResult(
            run_id=resolved_run_id,
            run_dir=final_dir,
            manifest_path=final_dir / "generation-manifest.json",
            data_dictionary_path=final_dir / "data-dictionary.json",
            summary_path=final_dir / "generation-summary.md",
            row_counts={dataset.dataset.filename: dataset.row_count for dataset in written},
        )
    except Exception:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise


def _generate_datasets(config: GenerationConfig) -> list[Dataset]:
    schedule = generate_schedule(config, make_rng(config.settings.seed, "schedule"))
    weather = generate_weather_events(config, make_rng(config.settings.seed, "weather"))
    airport_events = generate_airport_events(config, make_rng(config.settings.seed, "airport_events"))
    demand = generate_passenger_demand(config, schedule, make_rng(config.settings.seed, "demand"))
    aircraft_health = generate_aircraft_health(
        config,
        schedule,
        make_rng(config.settings.seed, "aircraft_health"),
    )
    crew = generate_crew_operations(
        config,
        schedule,
        weather,
        airport_events,
        make_rng(config.settings.seed, "crew"),
    )
    delays = generate_delay_history(
        config,
        schedule,
        weather,
        airport_events,
        aircraft_health,
        crew,
        make_rng(config.settings.seed, "delays"),
    )
    return [schedule, demand, weather, aircraft_health, crew, delays, airport_events]
