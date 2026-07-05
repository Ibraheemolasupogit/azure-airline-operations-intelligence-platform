# Milestone 4

## Objective

Build deterministic, governed, local-first passenger-demand forecasting using validated Milestone 3
outputs.

## Delivered Scope

- Passenger forecasting YAML profiles for development and CI.
- Validation-run discovery and processed dataset checksum verification.
- Booking-horizon modelling table construction.
- Feature availability and leakage policy.
- Chronological train, validation, and test splitting.
- Historical mean and booking-curve baselines.
- Lightweight deterministic linear-regression candidate model.
- MAE, RMSE, WAPE, sMAPE, bias, route-level, and load-factor-band metrics.
- Deterministic champion selection using validation metrics.
- Final test evaluation for the selected champion.
- Empirical prediction intervals and capacity constraints.
- Forecast outputs, model artefacts, metadata, lineage, model card, and reports.
- CLI commands for forecasting execution and completed-run description.
- Unit and integration tests for configuration, features, leakage, splitting, models, metrics,
  selection, artefacts, determinism, collision handling, and source rejection.

## Explicitly Deferred

- Flight-delay prediction.
- Aircraft-maintenance models.
- Disruption scoring.
- Route or schedule optimisation.
- GenAI functionality.
- Dashboards.
- Production monitoring.
- Azure infrastructure, SDK clients, credentials, or deployment workflows.

## Acceptance Criteria

Milestone 4 is accepted when `make quality` passes, CI-sized generation, validation, and passenger
forecasting all succeed, forecasts and model evidence are deterministic for identical inputs,
checksums reconcile, reports reflect actual run evidence, generated artefacts are ignored, and no
Milestone 5 or later functionality is implemented.
