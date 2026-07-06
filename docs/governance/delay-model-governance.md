# Delay Model Governance

Milestone 5 delay prediction is governed as a local, synthetic, reproducible model workflow.

## Evidence Requirements

- Every run must reference an explicit completed Milestone 3 validation report directory.
- Processed input checksums and row counts must reconcile to the validation manifest.
- Optional passenger forecast inputs must reconcile to the same validation run.
- Every generated output artefact is recorded in `delay-prediction-manifest.json`.
- Lineage links validation evidence, processed datasets, optional forecasts, features, model
  artefacts, predictions, and reports.

## Model Controls

- Chronological train, validation, and test splits are mandatory.
- Baselines are trained and compared before a candidate classifier can be selected.
- Champion and threshold selection use validation metrics only.
- Test metrics are reserved for final evidence after selection.
- Feature names are scanned for leakage-prone fields.
- Feature availability policies are written with the model artefacts.

## Responsible Use

The model is trained on synthetic data and supports demonstration workflows only. It is not a
certified operational decision system, dispatch authority, airworthiness signal, or safety
management control.

## Deferred Scope

No cloud deployment, Azure ML registry integration, monitoring, automated recovery action,
maintenance prediction, disruption scoring, optimisation, GenAI, or dashboard functionality is
implemented in Milestone 5.
