# Monitoring And Observability Architecture

Milestone 8 adds a deterministic local monitoring layer over completed airline operations
artefacts. It consumes explicit run directories, verifies manifests and checksums, extracts
metrics, evaluates health checks, performs deterministic drift-style comparison, generates
conservative alerts, and writes monitoring-ready outputs and reports.

The implementation is local-first and synthetic-data-only. It does not connect to Azure Monitor,
Application Insights, Log Analytics, Azure Data Explorer, Microsoft Purview, Power BI, Event Hubs,
or Azure Machine Learning.

## Components

- `monitoring.config` validates monitoring policy, thresholds, severity ordering, enabled domains,
  output paths, alert limits, seed, and accepted statuses.
- `monitoring.discovery` discovers explicit generation, validation, forecast, delay, maintenance,
  disruption, and baseline monitoring inputs.
- `monitoring.manifest_readers` reads manifests and verifies available checksums.
- `monitoring.metrics` extracts domain metrics from accepted manifests.
- `monitoring.checks` evaluates stable rule IDs such as `MON-VAL-003` and `MON-DISR-002`.
- `monitoring.drift` compares current metrics to a supplied baseline monitoring run.
- `monitoring.alerts` creates deterministic alert records from warning or failed checks.
- `monitoring.pipeline` writes outputs and reports atomically.

## Artefact Flow

See [monitoring observability flow](../../diagrams/monitoring-observability-flow.mmd).

## Output Contract

Each run writes to `outputs/monitoring/<monitoring_run_id>/`:

- `platform-health-summary.csv`
- `monitoring-metrics.csv`
- `monitoring-checks.jsonl`
- `monitoring-alerts.jsonl`
- `domain-health-summary.csv`
- `drift-comparison.csv`
- `monitoring-manifest.json`

Reports are written to `reports/monitoring/<monitoring_run_id>/`:

- `monitoring-summary.md`
- `platform-health-report.md`
- `monitoring-governance-report.md`
- `lineage.json`
- `monitoring-manifest.json`

## Future Azure Mapping

Local monitoring metrics map to future Azure Monitor custom metrics or Log Analytics tables.
Monitoring checks map to future scheduled query rules. Monitoring alerts map to future Azure
Monitor alert rules and Action Groups, but no routing is implemented in this milestone. Lineage
maps to Microsoft Purview, operational telemetry summaries map to Azure Data Explorer or Log
Analytics, model evidence maps to Azure Machine Learning metrics, and dashboard-ready summaries
map to Power BI in Milestone 10.
