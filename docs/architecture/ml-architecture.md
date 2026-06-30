# Machine-Learning Architecture

Future ML work will be evidence-led. No model is assumed superior because it is complex.
Baselines must be built, evaluated, and compared before advanced methods are adopted.

## Use Cases

- Passenger-demand forecasting.
- Flight-delay prediction.
- Aircraft-maintenance risk.
- Anomaly detection.
- Disruption scoring.
- Route-performance analysis.
- Optional schedule optimisation.

## Candidate Model Families

- Naive and seasonal baselines for forecasting and classification comparisons.
- ARIMA or SARIMA for time-series demand patterns.
- Prophet where calendar effects and interpretability justify its use.
- Logistic regression baselines for delay or disruption classification.
- Random forest models for nonlinear tabular signals.
- Gradient-boosted trees or XGBoost where tabular performance warrants extra complexity.
- Isolation forest for anomaly detection.
- LSTM models only when sequential evidence, data volume, and validation results justify them.

## Governance Requirements

- Chronological train, validation, and test splits.
- Leakage prevention for delay outcomes, future weather, passenger demand, and recovery actions.
- Deterministic seeds and reproducible training configuration.
- Baseline comparison before advanced models are accepted.
- Feature lineage from curated datasets to model inputs.
- Model metadata, training windows, code versions, and evaluation artefacts.
- Metrics tied to operational decisions, such as delay-risk triage quality or forecast error by
  route and departure period.
