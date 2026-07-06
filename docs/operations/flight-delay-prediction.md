# Flight-Delay Prediction

Milestone 5 predicts synthetic flight departure delay risk from a completed Milestone 3 validation
run.

## Run Prediction

```bash
python3 -m airline_operations_intelligence.cli predict-flight-delays \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/delay_prediction.yaml
```

With an optional passenger forecast:

```bash
python3 -m airline_operations_intelligence.cli predict-flight-delays \
  --validation-report-dir reports/validation/<validation_run_id> \
  --passenger-forecast-report-dir reports/passenger_forecasting/<forecast_run_id> \
  --config configs/delay_prediction.yaml
```

Useful CI-sized command:

```bash
python3 -m airline_operations_intelligence.cli predict-flight-delays \
  --validation-report-dir reports/validation/ci-quality \
  --config configs/delay_prediction_ci.yaml \
  --delay-run-id ci-quality \
  --overwrite
```

## Describe A Completed Run

```bash
python3 -m airline_operations_intelligence.cli describe-delay-prediction \
  --delay-report-dir reports/delay_prediction/<delay_run_id>
```

## Outputs

```text
outputs/delay_prediction/<delay_run_id>/
|-- delay_predictions.csv
|-- delay-metrics.csv
|-- grouped-delay-metrics.csv
|-- risk-band-summary.csv
|-- prediction-adjustments.csv
`-- delay-prediction-manifest.json

outputs/models/delay_prediction/<delay_run_id>/
|-- champion-model.json
|-- feature-schema.json
|-- feature-availability.json
|-- leakage-checks.json
|-- model-metadata.json
|-- training-metrics.json
|-- validation-metrics.json
|-- test-metrics.json
|-- candidate-comparison.csv
|-- threshold-comparison.csv
|-- calibration-metrics.csv
|-- calibration-bins.csv
|-- feature-importance.csv
|-- secondary-regression-metadata.json
|-- exclusion-summary.json
`-- environment.json

reports/delay_prediction/<delay_run_id>/
|-- delay-prediction-manifest.json
|-- delay-prediction-summary.md
|-- model-card.md
|-- evaluation-report.md
|-- feature-availability-report.md
`-- lineage.json
```

Generated prediction artefacts are local outputs and must not be committed.
