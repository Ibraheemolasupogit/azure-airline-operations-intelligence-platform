# Model Governance

Milestone 4 introduces local passenger-demand forecasting evidence. The workflow is deterministic,
auditable, and scoped to synthetic data.

## Controls

- Failed validation runs are rejected by default.
- Source processed checksums are verified before feature construction.
- Feature availability is recorded in `forecast-manifest.json`.
- Temporal leakage checks reject forbidden target, outcome, and post-departure features.
- Chronological train, validation, and test splits are recorded with boundaries.
- Champion selection uses validation metrics only.
- Test metrics are reported after champion selection.
- Forecast constraints and adjustments are written explicitly.
- Model artefacts and report artefacts are checksummed.

## Responsible Use

The passenger-demand model is a decision-support demonstration over fictional synthetic data. It
is not a production revenue-management model, pricing model, safety-critical system, or autonomous
operations-control system.

## Future Azure Mapping

Later milestones may map this workflow to Azure Machine Learning data assets, command jobs,
experiment tracking, registry candidates, Azure Monitor metrics, and Microsoft Purview lineage. No
Azure ML registration, endpoints, credentials, or cloud resources are created in Milestone 4.
