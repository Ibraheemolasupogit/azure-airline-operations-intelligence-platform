# Platform Monitoring Operations

Run monitoring against explicit completed artefacts:

```bash
python3 -m airline_operations_intelligence.cli monitor-platform \
  --generation-run-dir data/raw/<generation_run_id> \
  --validation-report-dir reports/validation/<validation_run_id> \
  --passenger-forecast-report-dir reports/passenger_forecasting/<forecast_run_id> \
  --delay-prediction-report-dir reports/delay_prediction/<delay_run_id> \
  --maintenance-report-dir reports/maintenance_analytics/<maintenance_run_id> \
  --disruption-report-dir reports/disruption_scoring/<disruption_run_id> \
  --config configs/monitoring.yaml
```

Only `--validation-report-dir` is required. Optional directories are accepted when supplied and
rejected when their lineage or integrity does not match the validation run.

Describe a completed monitoring run:

```bash
python3 -m airline_operations_intelligence.cli describe-monitoring \
  --monitoring-report-dir reports/monitoring/<monitoring_run_id>
```

Run the CI-sized local workflow:

```bash
make monitor-platform-ci
make describe-monitoring-ci
```

Run the full quality gate:

```bash
make quality
```

`make quality` runs the CI-sized pipeline through monitoring and then removes generated runtime
artefacts with `make clean`.

## Drift-Style Comparison

Supply a previous monitoring report directory:

```bash
python3 -m airline_operations_intelligence.cli monitor-platform \
  --validation-report-dir reports/validation/<validation_run_id> \
  --disruption-report-dir reports/disruption_scoring/<disruption_run_id> \
  --baseline-monitoring-report-dir reports/monitoring/<previous_monitoring_run_id> \
  --config configs/monitoring.yaml
```

Without a baseline, `drift-comparison.csv` is still produced with a skipped entry.

## Review Guidance

Review `platform-health-summary.csv` first, then `domain-health-summary.csv`,
`monitoring-checks.jsonl`, and `monitoring-alerts.jsonl`. Treat every alert as local synthetic
evidence requiring human review.
