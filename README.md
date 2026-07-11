# Azure Airline Operations Intelligence Platform

Azure Airline Operations Intelligence Platform is a local-first portfolio project that models a
governed airline operations intelligence workflow with deterministic synthetic data, validation,
analytics, monitoring, dashboard-ready exports, and Azure target-state architecture mapping. The
repository is designed to be cloned, inspected, validated locally, and discussed in interviews
without cloud access or real operational data.

No Azure resources are provisioned by this repository. The Azure content is target-state
architecture only, and all data is synthetic.

## Business Scenario

An airline operations control centre needs reliable evidence about demand, delay risk,
aircraft-health indicators, disruption severity, data quality, and executive reporting. This
repository demonstrates how those concerns can be organised into governed local pipelines before a
future Azure implementation is considered.

The platform is intentionally decision-support only. It is not a certified aviation system,
airworthiness tool, crew legality system, safety-management system, or operational decision
authority.

## Architecture Overview

The implemented local flow is:

```text
synthetic sources
-> raw data
-> validation
-> processed data
-> forecasting
-> delay prediction
-> maintenance analytics
-> disruption scoring
-> monitoring
-> deterministic GenAI-style assistant
-> dashboard-ready outputs
-> target-state Azure architecture mapping
```

The target-state Azure flow maps the same concerns to services such as Azure Event Hubs, Azure Data
Lake Storage Gen2, Azure Data Factory, Azure Machine Learning, Azure AI Foundry, Azure Monitor,
Microsoft Purview, Microsoft Fabric, and Power BI. These are documented mappings only; the repo
does not deploy, authenticate to, or call Azure, OpenAI, Fabric, or Power BI services.

Primary architecture references:

- [Final platform architecture](docs/architecture/final-platform-architecture.md)
- [Target architecture](docs/architecture/target-architecture.md)
- [Azure target architecture](docs/azure/azure-target-architecture.md)
- [Domain boundaries](docs/architecture/domain-boundaries.md)

## Implemented Capabilities By Milestone

| Milestone | Capability | Evidence |
| --- | --- | --- |
| 1 | Repository foundation and architecture baseline | package layout, CI, validation CLI, governance docs |
| 2 | Governed synthetic aviation data generation | seven datasets, manifest, checksums, data dictionary |
| 3 | Governed ingestion and validation | schema checks, quarantine, processed outputs, lineage |
| 4 | Passenger-demand forecasting | leakage-aware splits, baselines, forecasts, model card |
| 5 | Flight-delay prediction | deterministic classifier, thresholding, risk outputs |
| 6 | Aircraft-health and maintenance analytics | health features, risk bands, alerts, summaries |
| 7 | Operational disruption scoring | severity scores, alerts, operational summaries |
| 8 | Monitoring and observability | metric checks, alert evidence, drift-style comparison |
| 9 | GenAI-style operations assistant | evidence retrieval, guardrails, transcript, no live LLM |
| 10 | Power BI-ready dashboard output layer | star-schema CSV exports, KPI tables, semantic guidance |
| 11 | Azure deployment architecture and infrastructure mapping | target-state docs, reference-only IaC skeletons |
| 12 | Portfolio evidence and final polish | evidence pack, reviewer guide, final validation guidance |

The complete index is in
[milestone evidence index](docs/portfolio/milestone-evidence-index.md).

## Azure Service Mapping

| Platform capability | Azure target-state service |
| --- | --- |
| Event ingestion | Azure Event Hubs |
| Data orchestration | Azure Data Factory |
| Data lake storage | Azure Data Lake Storage Gen2 |
| Stream and operational analytics | Azure Stream Analytics and Azure Data Explorer |
| Analytical warehouse and lakehouse | Azure Synapse Analytics and Microsoft Fabric Lakehouse |
| Machine learning lifecycle | Azure Machine Learning |
| GenAI assistant pattern | Azure AI Foundry, Azure OpenAI, Azure AI Content Safety |
| Dashboard consumption | Microsoft Power BI |
| Monitoring | Azure Monitor, Application Insights, Log Analytics |
| Governance and lineage | Microsoft Purview |
| Identity and secrets | Microsoft Entra ID and Azure Key Vault |

See [capability matrix](docs/portfolio/capability-matrix.md) and
[Azure service mapping](docs/azure/azure-service-mapping.md).

## Repository Structure

```text
.
├── .github/workflows/          # Local CI quality workflow
├── configs/                    # Non-secret YAML configuration
├── dashboard/                  # Ignored local dashboard export zone
├── data/                       # Ignored local raw/interim/processed zones
├── diagrams/                   # Mermaid architecture and evidence diagrams
├── docs/                       # Architecture, governance, operations, milestones, portfolio
├── infra/                      # Reference-only Bicep/Terraform skeletons
├── outputs/                    # Ignored local analytics/model output zone
├── reports/                    # Ignored runtime reports plus committed architecture evidence
├── scripts/                    # Static validation helpers
├── src/airline_operations_intelligence/
│   ├── common/
│   ├── data_generation/
│   ├── ingestion/
│   ├── forecasting/
│   ├── delay_prediction/
│   ├── maintenance/
│   ├── disruption/
│   ├── monitoring/
│   ├── genai/
│   ├── dashboard/
│   └── validation/
└── tests/                      # Unit and integration tests
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make quality
```

The full quality gate is local. It creates a deterministic CI-sized synthetic run, validates it,
runs analytics through dashboard outputs, and removes the generated artefacts through `make clean`.

## Local Validation

Use the final validation guide for a reviewer-friendly walkthrough:

- [Final local validation guide](docs/operations/final-local-validation.md)

Common validation commands:

```bash
make validate
make validate-azure-architecture
make validate-portfolio-readiness
make quality
```

## Key CLI Examples

Generate synthetic data:

```bash
python3 -m airline_operations_intelligence.cli generate-data \
  --config configs/data_generation.yaml
```

Validate a generated run:

```bash
python3 -m airline_operations_intelligence.cli validate-data \
  --source-run-dir data/raw/<run_id> \
  --config configs/validation.yaml
```

Run forecasting, delay prediction, maintenance analytics, disruption scoring, monitoring,
assistant evidence, and dashboard exports with the milestone-specific commands documented under
[operations docs](docs/operations/final-local-validation.md).

## Quality Gate

`make quality` runs:

- Ruff lint and formatting checks;
- mypy type checking;
- pytest unit and integration tests;
- Markdown and YAML checks;
- repository foundation validation;
- Azure architecture static validation;
- portfolio readiness static validation;
- CI-sized generation, validation, analytics, monitoring, assistant, and dashboard outputs;
- cleanup of CI-generated runtime artefacts.

The GitHub Actions workflow mirrors these local checks without deployment steps.

## Generated Artefact Policy

Runtime data and reports are generated locally and ignored by git. The repo keeps placeholder files
so the directories exist, but generated data under `data/`, runtime outputs under `outputs/`,
dashboard exports under `dashboard/outputs/`, and milestone runtime reports under `reports/` should
not be committed.

Committed reports under `reports/architecture/` are static documentation evidence, not runtime
outputs.

## Evidence And Documentation Map

- [Portfolio evidence pack](docs/portfolio/portfolio-evidence-pack.md)
- [Milestone evidence index](docs/portfolio/milestone-evidence-index.md)
- [Interviewer guide](docs/portfolio/interviewer-guide.md)
- [Capability matrix](docs/portfolio/capability-matrix.md)
- [Final repository health report](reports/architecture/final-repository-health.md)
- [Roadmap](docs/milestones/roadmap.md)
- [Azure architecture evidence](reports/architecture/azure-architecture-evidence.md)

## Responsible Use

All datasets are synthetic and are designed for local demonstration. Model outputs, risk scores,
assistant responses, monitoring alerts, and dashboard summaries are evidence artefacts for portfolio
review only. They do not represent real passengers, employees, aircraft defects, airline schedules,
regulated safety decisions, or legally binding operational advice.

The deterministic GenAI-style assistant does not call a live LLM or external model. It retrieves
local evidence, applies guardrails, and marks responses for human review.

## Limitations

- No live Azure deployment, Azure SDK usage, cloud credentials, or managed identity integration.
- No live OpenAI or Azure OpenAI calls.
- No Power BI or Fabric publishing.
- No real-time streaming runtime.
- No optimisation engine or automated recovery action.
- No certified aviation safety, airworthiness, crew legality, or regulatory assurance claim.

## Future Work

Future milestones, outside the current repository scope, could add reviewed cloud deployment,
secured environment configuration, managed orchestration, live observability integration, richer
dashboard authoring, and production-grade model operations. Those would require separate security,
data protection, reliability, cost, and aviation-domain review before use with real systems.
