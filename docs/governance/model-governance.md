# Model Governance

Milestones 4, 5, and 6 introduce local passenger-demand forecasting, flight-delay prediction, and
aircraft-health maintenance analytics, and operational disruption scoring evidence. The workflows
are deterministic, auditable, and scoped to synthetic data.

## Controls

- Failed validation runs are rejected by default.
- Source processed checksums are verified before feature construction.
- Feature availability is recorded in model manifests and model artefacts.
- Maintenance analytics records sensor bounds, scoring weights, alert policy, lineage, and
  conservative human-review requirements.
- Temporal leakage checks reject forbidden target, outcome, and post-departure features.
- Chronological train, validation, and test splits are recorded with boundaries.
- Champion selection uses validation metrics only.
- Test metrics are reported after champion selection.
- Forecast constraints, delay risk bands, thresholds, and adjustments are written explicitly.
- Model artefacts and report artefacts are checksummed.

## Responsible Use

The passenger-demand, flight-delay, and maintenance analytics workflows are decision-support
demonstrations over fictional synthetic data. They are not production revenue-management models,
pricing models, certified predictive maintenance, safety-critical systems, dispatch authorities,
or autonomous operations-control systems.

## Future Azure Mapping

Later milestones may map this workflow to Azure Machine Learning data assets, command jobs,
experiment tracking, registry candidates, Azure Monitor metrics, and Microsoft Purview lineage. No
Azure ML registration, endpoints, credentials, or cloud resources are created in Milestones 4, 5,
or 6.
