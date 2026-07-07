# Azure Airline Operations Intelligence Platform

This repository is a local-first airline operations intelligence platform mapped to Microsoft
Azure services. The current implementation includes the repository foundation and governed
synthetic aviation data generation, ingestion, validation, passenger-demand forecasting,
flight-delay prediction, aircraft-health maintenance analytics, and operational disruption scoring.

No optimisation, GenAI assistants, dashboards, Azure infrastructure, deployment workflows, or
later-milestone monitoring functionality are implemented yet.

## Business Problem

An airline operations control centre needs a governed intelligence platform that combines
planned and real-time operational data to identify delay risk, forecast passenger demand,
monitor aircraft-health indicators, detect anomalies, assess disruption severity, understand
network impact, and support recovery decisions.

Initial data will be synthetic only. It must not represent real passengers, employees,
aircraft defects, confidential schedules, or proprietary airline operations.

## Intended Capabilities

- Flight operations data ingestion.
- Passenger-demand forecasting.
- Flight-delay prediction.
- Aircraft-health and predictive-maintenance analytics.
- Disruption-risk scoring.
- Recovery decision support.
- Operational monitoring.
- Power BI-ready analytical outputs.
- Governed GenAI-assisted operations intelligence.
- Azure architecture, governance, security, and deployment patterns.

## Azure Service Mapping

| Platform capability | Azure service |
| --- | --- |
| Event ingestion | Azure Event Hubs |
| Data lake storage | Azure Data Lake Storage Gen2 |
| Stream processing | Azure Stream Analytics |
| Operational telemetry analytics | Azure Data Explorer |
| Analytical warehouse | Azure Synapse Analytics |
| Machine learning | Azure Machine Learning |
| GenAI and agent capabilities | Azure AI Foundry |
| Business intelligence | Microsoft Power BI |
| Monitoring | Azure Monitor and Application Insights |
| Governance | Microsoft Purview |
| Identity and secrets | Microsoft Entra ID and Azure Key Vault |

## Architecture Summary

The target design uses synthetic aviation sources, local producers, a raw landing zone,
validation controls, curated datasets, analytical and machine-learning services, operational
outputs, reports, Power BI-ready artefacts, and future GenAI assistance. Cross-cutting
controls cover identity, secrets, lineage, audit logging, monitoring, CI/CD, data quality,
and model governance.

See [platform overview](docs/architecture/platform-overview.md) and
[target architecture](docs/architecture/target-architecture.md).

## Repository Structure

```text
.
├── .github/workflows/          # CI quality gate
├── configs/                    # Non-secret configuration
├── dashboard/                  # Future dashboard code
├── data/                       # Empty local data zones
├── diagrams/                   # Mermaid architecture diagrams
├── docs/                       # Architecture, governance, operations, milestones
├── outputs/                    # Future generated outputs, ignored by git
├── reports/                    # Future reports, ignored by git
├── scripts/                    # Future local automation scripts
├── src/airline_operations_intelligence/
│   ├── common/                 # Shared config, logging, exceptions
│   └── ...                     # Future domain packages
└── tests/                      # Unit, integration, and fixtures
```

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

Validate the repository foundation:

```bash
python3 -m airline_operations_intelligence.cli validate-repository
```

Generate a synthetic development run:

```bash
python3 -m airline_operations_intelligence.cli generate-data \
  --config configs/data_generation.yaml
```

Describe a completed run:

```bash
python3 -m airline_operations_intelligence.cli describe-generation \
  --run-dir data/raw/<run_id>
```

Validate a completed generation run:

```bash
python3 -m airline_operations_intelligence.cli validate-data \
  --source-run-dir data/raw/<run_id> \
  --config configs/validation.yaml
```

Describe a completed validation run:

```bash
python3 -m airline_operations_intelligence.cli describe-validation \
  --report-dir reports/validation/<validation_run_id>
```

Run passenger-demand forecasting:

```bash
python3 -m airline_operations_intelligence.cli forecast-passenger-demand \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/passenger_forecasting.yaml
```

Describe a completed forecast:

```bash
python3 -m airline_operations_intelligence.cli describe-passenger-forecast \
  --forecast-report-dir reports/passenger_forecasting/<forecast_run_id>
```

Run flight-delay prediction:

```bash
python3 -m airline_operations_intelligence.cli predict-flight-delays \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/delay_prediction.yaml
```

Describe a completed delay prediction run:

```bash
python3 -m airline_operations_intelligence.cli describe-delay-prediction \
  --delay-report-dir reports/delay_prediction/<delay_run_id>
```

Run aircraft-health analytics:

```bash
python3 -m airline_operations_intelligence.cli analyse-aircraft-health \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/maintenance_analytics.yaml
```

Run disruption scoring:

```bash
python3 -m airline_operations_intelligence.cli score-disruptions \
  --validation-report-dir reports/validation/<validation_run_id> \
  --config configs/disruption_scoring.yaml
```

## Quality Commands

```bash
make format      # Apply Ruff formatting and lint fixes
make lint        # Ruff lint and format checks
make typecheck   # mypy strict type checking
make test        # pytest
make docs-check  # Markdown checks
make yaml-check  # YAML checks
make validate    # Repository validation CLI
make generate-data-ci  # CI-sized deterministic synthetic data run
make validate-data-ci  # CI-sized governed validation run
make forecast-passenger-demand-ci  # CI-sized passenger forecasting run
make predict-flight-delays-ci  # CI-sized flight-delay prediction run
make analyse-aircraft-health-ci  # CI-sized aircraft-health analytics run
make score-disruptions-ci  # CI-sized disruption scoring run
make quality     # Full local gate
```

## Roadmap

Milestone 1 established the repository foundation. Milestone 2 added governed synthetic data
generation. Milestone 3 added governed local ingestion and validation. Milestone 4 added
passenger-demand forecasting. Milestone 5 added flight-delay prediction. Milestone 6 added
aircraft-health maintenance analytics. Milestone 7 adds operational disruption scoring. Later
milestones add monitoring, GenAI, Power BI outputs, and Azure deployment architecture.

See [roadmap](docs/milestones/roadmap.md).

## Responsible Use

This repository is an analytics and decision-support demonstration. It is not an airworthiness
system, flight-control system, safety-management system, or certified aviation operational
system. Future GenAI outputs must be grounded in governed evidence, distinguish facts from
recommendations, and keep humans responsible for consequential operational decisions.
