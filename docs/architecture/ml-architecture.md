# Machine-Learning Architecture

ML work is evidence-led. No model is assumed superior because it is complex. Baselines must be
built, evaluated, and compared before advanced methods are adopted.

## Use Cases

- Passenger-demand forecasting, implemented locally in Milestone 4.
- Flight-delay prediction, implemented locally in Milestone 5.
- Aircraft-maintenance risk, implemented locally in Milestone 6 as rules and statistical analytics.
- Anomaly detection.
- Disruption scoring, implemented locally in Milestone 7.
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

## Implemented Local Delay Prediction

- Consumes completed Milestone 3 validation runs and optionally compatible Milestone 4 passenger
  forecasts.
- Uses one prediction per scheduled flight with a configurable pre-departure cutoff.
- Prevents leakage from actual operations, delay outcomes, future events, and full-dataset target
  aggregates.
- Evaluates majority-class, route-history, and deterministic logistic-regression classifiers.
- Selects a champion and threshold using validation metrics only.
- Writes predictions, model artefacts, metrics, lineage, and reports locally.

## Implemented Local Maintenance Analytics

- Consumes completed Milestone 3 validation runs.
- Uses deterministic rules and statistical analytics rather than supervised predictive maintenance.
- Scores sensor thresholds, telemetry anomalies, degradation trends, fault-code evidence,
  utilisation, and retrospective operational context.
- Writes aircraft-level summaries, flight-level risk summaries, alerts, metrics, lineage, and
  reports locally.
