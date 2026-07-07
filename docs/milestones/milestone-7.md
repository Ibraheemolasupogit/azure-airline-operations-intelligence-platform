# Milestone 7

## Objective

Build deterministic, governed, local-first operational disruption scoring using validated
operational data from Milestone 3 and optional compatible analytics from Milestones 4, 5, and 6.

## Delivered Scope

- Disruption scoring YAML profiles for development and CI.
- Required validation source discovery and checksum verification.
- Optional passenger forecast, delay prediction, and maintenance analytics compatibility checks.
- Flight-level feature construction.
- Forward-risk leakage checks and retrospective outcome policy.
- Component scoring for delay, weather, airport events, crew, aircraft health, passenger pressure,
  and network reactionary pressure.
- Disruption severity scores, risk bands, recovery priorities, alerts, summaries, metrics,
  manifest, lineage, and reports.
- CLI commands for scoring and completed-run description.
- Unit and integration tests for configuration, scoring, alerts, summaries, pipeline outputs,
  determinism, collision handling, overwrite handling, and source rejection.

## Explicitly Deferred

- Route or schedule optimisation.
- GenAI summaries.
- Dashboards.
- Production monitoring.
- Azure infrastructure, SDK clients, credentials, deployments, or operational automation.
