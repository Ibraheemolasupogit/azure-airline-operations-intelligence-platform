# Maintenance Analytics Governance

Milestone 6 maintenance analytics are governed as deterministic synthetic evidence.

## Controls

- Runs require an explicit completed Milestone 3 validation report directory.
- Processed dataset checksums and row counts must match the validation manifest.
- Source discovery, feature engineering, scoring, alert generation, reporting, and lineage are
  separated in code.
- Scores are bounded to `[0, 1]` and component weights must sum to `1.0`.
- Alert text is conservative and always requires human review.
- Generated artefacts are ignored by git and must not be committed.

## Out Of Scope

The workflow does not implement certified predictive maintenance, airworthiness decisions,
maintenance planning, dispatch decisions, live monitoring, dashboards, GenAI, disruption scoring,
optimisation, Azure SDK clients, infrastructure deployment, or cloud credentials.

## Responsible Use

Outputs are synthetic analytics artefacts for portfolio demonstration. Real aircraft maintenance
requires licensed engineering inspection, certified systems, and regulated operational processes.
