# Milestone 3

## Objective

Build a governed, deterministic, local-first ingestion and validation workflow for synthetic
aviation datasets produced by Milestone 2.

## Delivered Scope

- Validation YAML profiles for development and CI.
- Explicit source-run discovery and generation manifest verification.
- Checksum, row-count, format, field-list, key, and safe-path verification.
- CSV and JSON Lines readers with conservative normalization.
- Schema, primary-key, dataset business-rule, and cross-dataset relationship validation.
- Structured validation results with stable rule identifiers and severities.
- Processed curated datasets containing valid records only.
- Dataset-specific quarantine files preserving invalid records and failure reasons.
- Validation manifest, validation results, quality metrics, lineage, and Markdown summary.
- CLI commands for validation execution and completed-run description.
- Unit and integration tests for valid, corrupted, deterministic, collision, overwrite, and fatal
  source-integrity paths.

## Explicitly Deferred

- Passenger-demand forecasting.
- Flight-delay prediction.
- Maintenance models.
- Disruption scoring.
- Optimisation.
- GenAI functionality.
- Dashboards.
- Azure infrastructure, credentials, SDK clients, or deployment workflows.
- Enterprise production monitoring.

## Acceptance Criteria

Milestone 3 is accepted when `make quality` passes, CI-sized generation and validation succeed,
valid records are written to processed outputs, invalid records are quarantined with explicit
reasons, reports reconcile counts and checksums, repeated validation is deterministic for business
outputs, and generated artefacts are not committed.
