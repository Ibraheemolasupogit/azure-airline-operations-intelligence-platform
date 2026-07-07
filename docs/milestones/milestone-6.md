# Milestone 6

## Objective

Build deterministic, governed, local-first aircraft-health and maintenance-risk analytics using
validated Milestone 3 operational data.

## Delivered Scope

- Maintenance analytics YAML profiles for development and CI.
- Validation source discovery, required field checks, row-count checks, and checksum verification.
- Aircraft telemetry feature engineering.
- Sensor threshold flags, robust statistical anomaly scoring, trend scoring, fault-code scoring,
  utilisation scoring, and retrospective operational context scoring.
- Bounded maintenance-risk score and inverse aircraft-health score.
- Risk bands, alert categories, conservative maintenance alerts, and human-review requirements.
- Aircraft-level summaries, flight-level maintenance-risk summaries, metrics, manifest, lineage,
  and reports.
- CLI commands for analytics execution and completed-run description.
- Unit and integration tests for configuration, features, scoring, alerts, pipeline outputs,
  determinism, collision handling, overwrite handling, and source rejection.

## Explicitly Deferred

- Disruption scoring.
- Route or schedule optimisation.
- GenAI functionality.
- Dashboards.
- Production monitoring.
- Azure infrastructure, SDK clients, credentials, deployments, or live alert routing.

## Acceptance Criteria

Milestone 6 is accepted when `make quality` passes, CI-sized generation and validation succeed,
aircraft-health analytics runs deterministically, manifest checksums reconcile, reports reflect
actual evidence, generated artefacts are ignored and cleaned, and no Milestone 7 or later
functionality is implemented.
