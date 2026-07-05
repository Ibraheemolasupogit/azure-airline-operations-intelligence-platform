# Passenger Forecasting

Milestone 4 forecasts final synthetic passenger demand from a completed Milestone 3 validation
run.

## Run Forecasting

```bash
python3 -m airline_operations_intelligence.cli forecast-passenger-demand \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/passenger_forecasting.yaml
```

Useful CI-sized command:

```bash
python3 -m airline_operations_intelligence.cli forecast-passenger-demand \
  --validation-report-dir reports/validation/ci-quality \
  --config configs/passenger_forecasting_ci.yaml \
  --forecast-run-id ci-quality \
  --overwrite
```

## Describe A Completed Forecast

```bash
python3 -m airline_operations_intelligence.cli describe-passenger-forecast \
  --forecast-report-dir reports/passenger_forecasting/<forecast_run_id>
```

## Outputs

```text
outputs/passenger_forecasting/<forecast_run_id>/
├── passenger_forecast.csv
├── forecast-metrics.csv
├── route-forecast-summary.csv
├── forecast-adjustments.csv
└── forecast-manifest.json

outputs/models/passenger_forecasting/<forecast_run_id>/
├── champion-model.json
├── feature-schema.json
├── model-metadata.json
├── training-metrics.json
├── validation-metrics.json
├── test-metrics.json
├── candidate-comparison.csv
├── feature-importance.csv
├── residual-distribution.json
├── prediction-interval-metadata.json
└── environment.json

reports/passenger_forecasting/<forecast_run_id>/
├── forecast-manifest.json
├── forecasting-summary.md
├── model-card.md
├── evaluation-report.md
└── lineage.json
```

Generated forecasting artefacts are local outputs and must not be committed.
