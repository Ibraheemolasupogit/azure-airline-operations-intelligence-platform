# Final Platform Architecture

## End-To-End Flow

The repository implements a local-first architecture that moves deterministic synthetic aviation
sources through governed data, analytics, monitoring, assistant, and reporting layers:

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
-> GenAI assistant
-> dashboard outputs
-> Azure target architecture
```

## Local Flow

Synthetic source files are generated under `data/raw/<run_id>`. The validation layer reads those
files, applies schema and business checks, writes accepted records to processed zones, writes
quarantine evidence for invalid records, and produces validation reports. Analytics components then
consume validation evidence rather than bypassing data-quality controls.

Passenger forecasting, delay prediction, maintenance analytics, and disruption scoring each produce
local outputs and reports with counts, metrics, lineage, and deterministic configuration evidence.
Monitoring reads the generated artefacts explicitly and records checks, metrics, alerts, and
drift-style evidence. The deterministic GenAI-style assistant retrieves local evidence and produces
guardrailed response artefacts. Dashboard output generation creates Power BI-ready CSV tables,
metadata, data dictionaries, and quality evidence without publishing anything.

## Azure Target Flow

The target-state Azure architecture maps source ingestion to Event Hubs and Data Factory, storage
zones to ADLS Gen2, analytics and modelling to Azure Machine Learning and related services,
observability to Azure Monitor and Log Analytics, governance to Microsoft Purview, assistant
patterns to Azure AI Foundry, and BI consumption to Power BI and Microsoft Fabric.

This is documentation only. No Azure resources are provisioned, no deployment commands are run, and
no Azure SDK, OpenAI SDK, Power BI API, or Fabric API dependency is introduced.

## Domain Boundaries

- Data generation owns fictional source records and data dictionaries.
- Ingestion and validation own source discovery, schema checks, quarantine, and processed evidence.
- Analytics domains own deterministic features, metrics, lineage, and reports.
- Monitoring owns local artefact checks and alert evidence.
- The assistant owns local evidence retrieval, guardrails, prompt audit, and transcript artefacts.
- Dashboard exports own dimensional tables and BI handoff documentation.
- Azure docs and `infra/` own target-state mapping only.

## Data Contracts

Data contracts are expressed through YAML config, generated data dictionaries, validation rules,
manifest row counts, checksums, and test expectations. Downstream domains consume validated report
directories and generated artefact paths, not hidden global state.

## Artefact Lineage

Each generated run uses explicit run IDs and writes reports that connect input directories,
configuration files, output files, row counts, and checksums. The lineage chain is visible from raw
generation through dashboard outputs and is summarised in the milestone evidence index.

## Security And Governance

The repository uses non-secret example configuration, `.gitignore` protections, static validators,
and documentation boundaries. It contains no real tenant IDs, subscription IDs, client secrets,
endpoints, Terraform state, or live credentials. Reference-only IaC skeletons are deliberately
non-deploying.

## Responsible-Use Controls

All data and outputs are synthetic. Scores, alerts, model outputs, assistant responses, and
dashboard metrics are portfolio evidence only and require human review. The repository does not
claim certified aviation safety, airworthiness, crew legality, production monitoring, or
operational decision authority.

## Quality Gates

`make quality` runs lint, format checks, type checks, tests, Markdown checks, YAML checks,
repository validation, Azure architecture validation, portfolio readiness validation, CI-sized
pipeline generation through dashboard outputs, and cleanup.
