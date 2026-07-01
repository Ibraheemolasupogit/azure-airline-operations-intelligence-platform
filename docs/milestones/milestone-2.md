# Milestone 2

## Objective

Build a deterministic, configurable, well-tested synthetic aviation data-generation layer.

## Delivered Scope

- YAML-driven development and CI generation profiles.
- Seven required synthetic datasets under `data/raw/<run_id>/`.
- Atomic run-directory output handling.
- Deterministic run IDs with explicit `--run-id` override.
- Collision rejection and controlled overwrite.
- Generation manifest with configuration snapshot, fingerprint, row counts, checksums, keys,
  event-time bounds, counts, warnings, declaration, and limitations.
- Data dictionary covering every generated field.
- Markdown generation summary based on actual run metadata.
- CLI commands for generation and completed-run description.
- Unit and integration tests for configuration, determinism, relationships, checksums, manifests,
  data dictionary coverage, collision behaviour, and domain logic.

## Explicitly Deferred

- Ingestion pipelines.
- Formal validation pipelines.
- Forecasting, prediction, maintenance, disruption, and optimisation models.
- GenAI functionality.
- Dashboards.
- Azure infrastructure or deployment workflows.

## Acceptance Criteria

Milestone 2 is accepted when `make quality` passes, a development generation run succeeds, the
manifest checksums match actual files, repeated runs with the same seed reproduce business-data
checksums, and generated outputs are not committed.
