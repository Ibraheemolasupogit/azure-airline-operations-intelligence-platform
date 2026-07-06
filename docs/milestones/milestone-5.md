# Milestone 5

## Objective

Build deterministic, governed, local-first flight-delay prediction using validated Milestone 3
outputs, with optional Milestone 4 passenger forecast features.

## Delivered Scope

- Delay prediction YAML profiles for development and CI.
- Validation-run discovery, required dataset checks, row-count checks, and processed checksum
  verification.
- Optional passenger forecast compatibility checks.
- Flight-level modelling table with a configurable pre-departure cutoff.
- Leakage policy and feature availability evidence.
- Chronological train, validation, and test splitting.
- Majority-class and route-history baselines.
- Lightweight deterministic logistic-regression candidate classifier.
- ROC AUC, PR AUC, log loss, Brier score, precision, recall, F1, specificity, balanced accuracy,
  grouped metrics, calibration bins, and risk-band summaries.
- Validation-only champion and threshold selection.
- Test predictions, model artefacts, metadata, lineage, model card, evaluation, and feature
  availability reports.
- CLI commands for prediction execution and completed-run description.
- Unit and integration tests for configuration, leakage, splitting, modelling, metrics, selection,
  determinism, collision handling, and source rejection.

## Explicitly Deferred

- Aircraft-maintenance models.
- Disruption scoring.
- Route or schedule optimisation.
- GenAI functionality.
- Dashboards.
- Production monitoring.
- Azure infrastructure, SDK clients, credentials, deployments, or model registry integration.

## Acceptance Criteria

Milestone 5 is accepted when `make quality` passes, CI-sized generation, validation, passenger
forecasting, and delay prediction all succeed, one development smoke run succeeds, deterministic
reproduction is demonstrated for the same config and seed, manifest checksums reconcile, generated
artefacts are ignored and cleaned, and no Milestone 6 or later functionality is implemented.
