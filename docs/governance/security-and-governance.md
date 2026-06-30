# Security And Governance

## Core Principles

- Apply least privilege to local workflows and future Azure resources.
- Use managed identities in the Azure target state wherever practical.
- Store secrets in Azure Key Vault, never in repository files.
- Separate local, development, test, and production environments.
- Encrypt data at rest and in transit in the Azure target state.
- Classify data by sensitivity and business impact.
- Keep Milestone 1 and future sample data synthetic.
- Log security-relevant events and retain audit evidence according to policy.
- Track model lineage, evaluation, approvals, and limitations.
- Govern prompts, retrieved context, responses, and GenAI audit logs.
- Preserve lineage from source records to curated datasets, outputs, and reports.
- Define retention expectations before storing operational outputs.
- Require reproducibility for data generation, validation, and modelling.
- Apply responsible-AI review for models and GenAI features.

## Synthetic-Data Controls

Synthetic data must not encode real passengers, employees, confidential schedules, actual
aircraft defects, or proprietary operational incidents. Generated records should be clearly
labelled synthetic and suitable for local demonstration only.

## Aviation Safety Boundary

The platform is an analytics and decision-support demonstration. It is not an airworthiness
system, flight-control system, safety-management system, or certified aviation operational
system. Humans remain accountable for consequential operational decisions.
