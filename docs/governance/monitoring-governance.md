# Monitoring Governance

Milestone 8 monitoring is governed local evidence over fictional synthetic data. It is intended
for portfolio demonstration, auditability, and future Azure mapping. It is not live production
monitoring, certified aviation monitoring, SRE-grade observability, or a safety-critical alerting
system.

## Controls

- Inputs must be explicit. The workflow never selects the latest run silently.
- Validation, generation, analytics, and scoring manifests are parsed by type.
- Manifest and available artefact checksums are verified before metrics are produced.
- Optional upstream runs must reference the same Milestone 3 validation run.
- Warning and failed checks create conservative local alerts only.
- Alert ordering is deterministic by severity and rule ID.
- Drift comparison is relative-change evidence, not statistical production drift detection.
- Human review is required for all monitoring interpretation.

## Severity Policy

The configuration maps severities to ordered values:

- `info`: normal evidence.
- `warning`: review-worthy threshold crossing.
- `high`: material local monitoring concern.
- `critical`: integrity or severe threshold concern.

The policy is validated to be strictly increasing.

## Responsible Use

Monitoring outputs must not be used to evaluate real passengers, crew, engineers, operators,
aircraft, or airline performance. Outputs must not autonomously trigger operational actions,
incident tickets, emails, messages, maintenance action, or recovery decisions.

## Exclusions

This milestone does not implement Azure SDK clients, Azure Monitor clients, Application Insights
clients, Event Hubs clients, Azure Data Explorer clients, Terraform, Bicep, ARM templates,
subscription IDs, cloud credentials, dashboards, GenAI summaries, or alert routing.
