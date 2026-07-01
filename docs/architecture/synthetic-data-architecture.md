# Synthetic Data Architecture

Milestone 2 adds deterministic synthetic aviation data generation. The generator creates
fictional operational datasets that are relationally coherent enough to support later ingestion,
validation, forecasting, prediction, maintenance analytics, disruption scoring, reporting, and
GenAI grounding work.

## Why Synthetic Data

The repository must not contain real passenger data, employee data, aircraft defects,
confidential schedules, airport incidents, or proprietary airline operations. Synthetic data
lets the platform demonstrate realistic relationships and operational patterns while remaining
safe for local development and CI.

## Generation Flow

```text
YAML generation profile
    -> configuration validation
    -> deterministic run ID and seeded domain RNGs
    -> schedule, weather and airport event generation
    -> demand, telemetry, crew and delay generation
    -> generation-time invariants
    -> atomic write to data/raw/<run_id>/
    -> manifest, data dictionary and summary
```

Generation logic is split by domain under
`src/airline_operations_intelligence/data_generation/`. The orchestrator coordinates the run but
does not contain all generation logic.

## Dataset Grains

- `flight_schedule.csv`: one row per scheduled flight leg.
- `passenger_demand.csv`: one row per flight demand observation.
- `weather_events.csv`: one row per airport weather observation or event window.
- `aircraft_health.jsonl`: one telemetry observation per aircraft and timestamp.
- `crew_operations.csv`: one row per crew assignment to a scheduled flight.
- `delay_history.csv`: one row per completed or simulated flight outcome.
- `airport_events.jsonl`: one airport operational event per event window.

## Relationships

The generator maintains these minimum relationships:

- `passenger_demand.flight_id`, `crew_operations.flight_id`, `delay_history.flight_id` and
  `aircraft_health.flight_id` reference `flight_schedule.flight_id`.
- `flight_schedule.aircraft_id` and `aircraft_health.aircraft_id` reference configured fleet
  aircraft.
- Flight origin and destination, weather airport codes, and airport-event airport codes reference
  the configured airport dimension.
- Route IDs map consistently to configured origin-destination pairs.

## Deterministic Design

Domain-specific random generators are derived from the configured seed and a domain namespace.
Business records avoid current timestamps and random UUIDs. Default run IDs are derived from the
profile, start date, duration, seed, and configuration fingerprint. Manifest generation time is
allowed to reflect execution time, but it does not affect business-data checksums.

## Generation Invariants

Milestone 2 includes lightweight generation-time invariants for uniqueness, timestamp ordering,
foreign-key references, route consistency, passenger count bounds, score ranges, and non-empty
outputs. These checks are not a comprehensive data-quality validation pipeline. Milestone 3 will
introduce governed ingestion and formal validation.

## Azure Mapping

- Local generation producers map to future Event Hubs producers or scheduled data-generation jobs.
- `data/raw/<run_id>/` maps to an ADLS Gen2 raw landing zone.
- `generation-manifest.json` maps to governed ingestion metadata and lineage input.
- `data-dictionary.json` is a Microsoft Purview metadata candidate.
- `generation-summary.md` is an operational evidence artefact.

No Azure resources, credentials, Terraform, Bicep, or deployment workflows are introduced in this
milestone.
