# Model Governance

Milestones 4 through 9 introduce local passenger-demand forecasting, flight-delay prediction,
aircraft-health maintenance analytics, operational disruption scoring, monitoring evidence, and a
deterministic local GenAI-style assistant. The workflows are deterministic, auditable, and scoped
to synthetic data.

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
- Monitoring evidence verifies manifests, checksums, lineage compatibility, metric extraction,
  checks, alerts, drift-style comparisons, and local reports.
- Assistant evidence verifies manifests, extracts structured evidence, ranks retrieved context,
  writes prompt audit records, cites evidence IDs, records guardrails, and writes transcripts.

## Responsible Use

The passenger-demand, flight-delay, maintenance analytics, disruption scoring, and monitoring
workflows are decision-support demonstrations over fictional synthetic data. They are not
production revenue-management models, pricing models, certified predictive maintenance,
safety-critical systems, dispatch authorities, live observability systems, live LLM systems, or
autonomous operations-control systems.

## Future Azure Mapping

Later milestones may map this workflow to Azure Machine Learning data assets, command jobs,
experiment tracking, registry candidates, Azure Monitor metrics, Log Analytics tables, and
Microsoft Purview lineage. No Azure ML registration, endpoints, credentials, Azure Monitor clients,
OpenAI SDKs, model endpoints, or cloud resources are created in Milestones 4 through 9.
