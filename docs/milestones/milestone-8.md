# Milestone 8 - Monitoring And Observability

Milestone 8 implements local monitoring evidence for the completed airline operations platform
pipeline through operational disruption scoring.

## Delivered Scope

- Monitoring configuration files for development and CI.
- `monitor-platform` and `describe-monitoring` CLI commands.
- Manifest parsing for generation, validation, passenger forecasting, delay prediction,
  maintenance analytics, disruption scoring, and monitoring baseline runs.
- Checksum verification for manifests and available artefacts, including validation processed
  outputs.
- Metrics across generation, validation, passenger forecasting, delay prediction, maintenance
  analytics, and disruption scoring.
- Stable monitoring checks with `MON-*` rule IDs.
- Deterministic alert generation from warning and failed checks.
- Domain and platform health summaries.
- Drift-style relative-change comparison when a baseline monitoring run is supplied.
- Atomic output and report writing.
- Monitoring manifest, lineage, and governance reports.
- CI-sized Makefile and GitHub Actions integration.

## Acceptance Evidence

The monitoring test target exercises configuration validation, manifest discovery, checksum
verification, compatibility rejection, metric extraction, checks, alerts, drift, summaries,
collision protection, overwrite behavior, and completed-run description.

The CI target runs generation, validation, passenger forecasting, delay prediction, maintenance
analytics, disruption scoring, and monitoring locally with no cloud credentials.

## Out Of Scope

Milestone 8 does not implement GenAI, dashboards, route or schedule optimisation, Azure
infrastructure deployment, live telemetry ingestion, Azure Monitor integration, Application
Insights integration, alert routing, or Milestone 9+ functionality.

## Responsible Use

Monitoring outputs are fictional synthetic evidence. They are not certified aviation monitoring,
not live production observability, not incident management automation, and not safety-critical
alerting.
