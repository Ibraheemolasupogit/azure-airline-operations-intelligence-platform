# Machine-Learning Architecture

ML work is evidence-led. No model is assumed superior because it is complex. Baselines must be
built, evaluated, and compared before advanced methods are adopted.

## Use Cases

- Passenger-demand forecasting, implemented locally in Milestone 4.
- Flight-delay prediction.
- Aircraft-maintenance risk.
- Anomaly detection.
- Disruption scoring.
- Route-performance analysis.
- Optional schedule optimisation.

## Candidate Model Families

- Naive and historical baselines for forecasting and classification comparisons.
- Lightweight supervised regressors where the modelling grain is flight-level prediction.
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

## Implemented Local Forecasting

- Consumes completed Milestone 3 validation runs.
- Uses one forecast per flight at a configured booking horizon.
- Prevents temporal leakage through feature availability policy and chronological splits.
- Evaluates historical mean, booking-curve, and deterministic linear-regression candidates.
- Selects a champion using validation metrics only.
- Writes model artefacts, forecasts, metrics, lineage, and reports locally.
