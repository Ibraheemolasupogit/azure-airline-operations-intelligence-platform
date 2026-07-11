# Portfolio Evidence Pack

## Project Summary

Azure Airline Operations Intelligence Platform is a local-first portfolio repository that
demonstrates how an airline operations intelligence platform can be structured, validated, and
explained without using real airline data or provisioning cloud resources.

The implemented platform produces deterministic synthetic aviation data, validates and quarantines
records, builds analytical and machine-learning evidence, monitors generated artefacts, creates a
deterministic GenAI-style assistant response, exports Power BI-ready tables, and maps the result to
a target-state Azure architecture.

## Business Problem

Airline operations teams need a governed way to understand passenger demand, delay risk,
aircraft-health indicators, disruption severity, data quality, and executive reporting. The
repository models that problem as a traceable evidence pipeline rather than as a live operational
system.

## Target Users

- Data and analytics engineers reviewing data contracts, lineage, and repeatable pipelines.
- ML engineers reviewing deterministic modelling evidence and leakage controls.
- Cloud architects reviewing Azure service mapping and deployment boundaries.
- Governance reviewers reviewing synthetic-data, responsible-use, and no-secret controls.
- Recruiters or interviewers looking for a concise technical portfolio walkthrough.

## End-To-End Platform Capabilities

1. Synthetic aviation source generation.
2. Governed ingestion and validation.
3. Passenger-demand forecasting.
4. Flight-delay prediction.
5. Aircraft-health and maintenance analytics.
6. Operational disruption scoring.
7. Local monitoring and observability evidence.
8. Deterministic GenAI-style operations assistant.
9. Power BI-ready dashboard exports.
10. Target-state Azure architecture and infrastructure mapping.
11. Portfolio evidence, reviewer guidance, and readiness validation.

## Local-First Implementation Summary

The repository runs entirely from local Python commands and `make` targets. YAML configuration files
control deterministic synthetic data, validation rules, analytics profiles, monitoring thresholds,
assistant guardrails, and dashboard output definitions. Runtime artefacts are written under ignored
local folders and cleaned after CI-sized quality runs.

## Azure Target-State Summary

Azure documentation maps local capabilities to Azure Event Hubs, Azure Data Lake Storage Gen2,
Azure Data Factory, Azure Machine Learning, Azure AI Foundry, Azure Monitor, Microsoft Purview,
Microsoft Fabric, Power BI, Microsoft Entra ID, and Azure Key Vault. The mapping is reference-only:
no Azure SDK clients, credentials, service principals, deployment commands, or cloud resources are
introduced.

## Milestone-By-Milestone Evidence

| Milestone | Evidence |
| --- | --- |
| 1 | Repository layout, Makefile, CI workflow, validation CLI, baseline architecture docs. |
| 2 | Seven deterministic synthetic datasets, manifest checksums, data dictionary, summaries. |
| 3 | Validation reports, processed datasets, quarantine handling, lineage evidence. |
| 4 | Forecast outputs, metrics, partition evidence, model card, lineage. |
| 5 | Delay risk predictions, threshold evidence, metrics, model report. |
| 6 | Maintenance risk features, alerts, aircraft summaries, flight risk outputs. |
| 7 | Disruption severity scores, alerts, route/airport/aircraft/daily summaries. |
| 8 | Monitoring metrics, checks, alerts, drift-style comparison, evidence report. |
| 9 | Retrieved evidence, guardrail checks, prompt audit, transcript, assistant report. |
| 10 | Star-schema CSV exports, KPI tables, semantic guidance, data dictionary, lineage. |
| 11 | Azure service mapping, governance docs, reference-only IaC skeletons, static validation. |
| 12 | Portfolio pack, evidence index, interviewer guide, capability matrix, readiness checks. |

See [milestone evidence index](milestone-evidence-index.md) for the full review map.

## Quality And CI Evidence

The full local quality gate is `make quality`. It runs linting, formatting checks, type checking,
unit and integration tests, Markdown and YAML checks, repository validation, Azure architecture
validation, portfolio readiness validation, a CI-sized data and analytics generation flow, and
cleanup.

The GitHub Actions workflow mirrors those local checks and intentionally contains no deployment
steps.

## Governance And Responsible-Use Boundaries

- All generated data is synthetic.
- Outputs are demonstration evidence, not live operational recommendations.
- The assistant is deterministic and local; it does not call a live LLM.
- Dashboard exports are local files; no Power BI or Fabric publishing occurs.
- Azure architecture is target-state only; no Azure resources are provisioned.
- No secrets, real identifiers, real endpoints, or credentials are required.

## Interview Talking Points

- How deterministic generation and manifests support reproducibility.
- How validation separates accepted and quarantined records.
- How ML outputs include lineage, metrics, and model cards.
- How monitoring verifies explicit local artefacts.
- How assistant responses are grounded in local evidence and guardrails.
- How Power BI-ready exports are structured without publishing.
- How Azure mapping is documented without overclaiming deployment.
- How quality gates prevent generated artefacts and unsafe claims from entering the repo.

## Technical Demonstration

The repository demonstrates Python package design, configuration-driven pipelines, local data
contracts, deterministic analytics, testable CLI workflows, CI discipline, documentation
architecture, static safety validation, synthetic-data governance, and Azure solution design.

## What This Repository Does Not Claim

This repository does not claim to be production-ready, enterprise certified, deployed to Azure,
powered by live Azure OpenAI, connected to Power BI, or suitable for real aviation operational
decision authority. It is a professional portfolio artefact and local demonstration platform.
