# Dashboard Outputs

Build local dashboard-ready exports with explicit source directories:

```bash
python -m airline_operations_intelligence.cli build-dashboard-outputs \
  --generation-run-dir data/raw/ci-quality \
  --validation-report-dir reports/validation/ci-quality \
  --passenger-forecast-report-dir reports/passenger_forecasting/ci-quality \
  --delay-prediction-report-dir reports/delay_prediction/ci-quality \
  --maintenance-report-dir reports/maintenance_analytics/ci-quality \
  --disruption-report-dir reports/disruption_scoring/ci-quality \
  --monitoring-report-dir reports/monitoring/ci-quality \
  --config configs/dashboard_outputs_ci.yaml \
  --dashboard-run-id ci-quality \
  --overwrite
```

Describe a completed run without rebuilding:

```bash
python -m airline_operations_intelligence.cli describe-dashboard-outputs \
  --dashboard-report-dir reports/dashboard_outputs/ci-quality
```

Run-specific outputs are written under `dashboard/outputs/<dashboard_run_id>/` and reports under
`reports/dashboard_outputs/<dashboard_run_id>/`. Normal generated outputs are ignored by Git and
removed by `make clean` for the CI run ID.
