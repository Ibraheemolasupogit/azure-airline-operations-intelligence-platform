# Aircraft-Health Analytics

Run Milestone 6 aircraft-health and maintenance analytics from a completed Milestone 3 validation
run.

## Run Analytics

```bash
python3 -m airline_operations_intelligence.cli analyse-aircraft-health \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/maintenance_analytics.yaml
```

Useful CI-sized command:

```bash
python3 -m airline_operations_intelligence.cli analyse-aircraft-health \
  --validation-report-dir reports/validation/ci-quality \
  --config configs/maintenance_analytics_ci.yaml \
  --maintenance-run-id ci-quality \
  --overwrite
```

## Describe A Completed Run

```bash
python3 -m airline_operations_intelligence.cli describe-aircraft-health \
  --maintenance-report-dir reports/maintenance_analytics/<maintenance_run_id>
```

## Outputs

```text
outputs/maintenance_analytics/<maintenance_run_id>/
|-- aircraft_health_features.csv
|-- aircraft_health_scores.csv
|-- maintenance_alerts.jsonl
|-- aircraft_health_summary.csv
|-- flight_maintenance_risk.csv
|-- maintenance-metrics.csv
`-- maintenance-analytics-manifest.json

reports/maintenance_analytics/<maintenance_run_id>/
|-- maintenance-analytics-manifest.json
|-- maintenance-analytics-summary.md
|-- aircraft-health-report.md
|-- maintenance-governance-report.md
`-- lineage.json
```

Generated outputs are local artefacts and must not be committed.
