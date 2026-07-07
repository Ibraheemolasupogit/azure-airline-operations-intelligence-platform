# Disruption Scoring

Run Milestone 7 operational disruption scoring from a completed Milestone 3 validation run.

## Run Scoring

```bash
python3 -m airline_operations_intelligence.cli score-disruptions \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/disruption_scoring.yaml
```

Optional upstream analytics can be supplied explicitly:

```bash
python3 -m airline_operations_intelligence.cli score-disruptions \
  --validation-report-dir reports/validation/<validation_run_id> \
  --passenger-forecast-report-dir reports/passenger_forecasting/<forecast_run_id> \
  --delay-prediction-report-dir reports/delay_prediction/<delay_run_id> \
  --maintenance-report-dir reports/maintenance_analytics/<maintenance_run_id> \
  --config configs/disruption_scoring.yaml
```

## Outputs

```text
outputs/disruption_scoring/<disruption_run_id>/
|-- disruption_features.csv
|-- disruption_scores.csv
|-- disruption_alerts.jsonl
|-- route_disruption_summary.csv
|-- airport_disruption_summary.csv
|-- aircraft_disruption_summary.csv
|-- daily_disruption_summary.csv
|-- disruption-metrics.csv
`-- disruption-scoring-manifest.json

reports/disruption_scoring/<disruption_run_id>/
|-- disruption-scoring-manifest.json
|-- disruption-scoring-summary.md
|-- disruption-evidence-report.md
|-- disruption-governance-report.md
`-- lineage.json
```
