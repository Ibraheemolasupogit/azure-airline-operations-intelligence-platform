# Domain Boundaries

Each domain owns its public contracts and future outputs. Domains should exchange governed
datasets, schemas, configuration objects, or documented service interfaces. They should not
import arbitrary internal modules from each other.

## Data Generation

Creates deterministic synthetic aviation datasets with no real passengers, employees,
aircraft defects, or confidential operations.

## Ingestion

Reads completed synthetic source runs, verifies generation manifests, parses source records, and
preserves source metadata and lineage. The production mapping is Azure Event Hubs and ADLS Gen2.

## Validation

Enforces schema, primary-key, range, timestamp, referential-integrity, and synthetic business rules
before records become curated operational datasets.

## Passenger Forecasting

Forecasts final synthetic passenger demand by flight at a configured booking horizon using
validated data, leakage-safe features, chronological splits, baselines, model evidence, and
operationally meaningful metrics.

## Delay Prediction

Will estimate flight-delay risk from governed schedule, weather, airport, and delay-history
features without leaking future information.

## Aircraft Maintenance Analytics

Will analyse synthetic aircraft-health indicators for anomaly and maintenance-risk signals.
It will remain decision-support only and will not represent airworthiness certification.

## Disruption Scoring

Will combine delay risk, passenger impact, network position, crew and airport constraints, and
recovery context into transparent disruption-severity evidence.

## Route And Schedule Optimisation

Will explore schedule and route-performance scenarios only after analytical evidence exists.
Recommendations must include constraints, assumptions, and human review.

## GenAI Operations Assistance

Answers controlled operational-assistant intents from governed local evidence using deterministic
templates. It cites evidence IDs, writes prompt and transcript audit artefacts, applies guardrails,
and avoids autonomous operational action. It does not call live LLMs or Azure AI services.

## Monitoring

Collects local pipeline, data-quality, model-evidence, analytics, lineage, drift-style, and alert
evidence from explicit completed artefacts. Azure Monitor, Log Analytics, Application Insights,
Data Explorer, Microsoft Purview, Azure Machine Learning, and Power BI are documentation mappings
only.

## Reporting

Produces operational reports and Power BI-ready outputs from governed datasets and model evidence,
not from raw or private implementation details.

## Dashboard Outputs

Consumes explicit completed validation, analytics, monitoring, and optional assistant artefacts.
It verifies manifests and checksums, rejects incompatible lineage, and produces local analytical
tables, KPI summaries, semantic-model documentation, measure catalogues, page specs, data
dictionaries, lineage, and reports. It does not publish to Power BI or Fabric and does not call
Azure, Power BI, Fabric, OpenAI, or external APIs.

## Azure Architecture Mapping

Documents the target-state Azure architecture for implemented local capabilities. It owns service
mapping, data-zone mapping, environment strategy, security, governance, MLOps, GenAI, monitoring,
dashboard consumption, and reference-only infrastructure skeletons. It does not deploy resources
or introduce live cloud clients.

## Portfolio Evidence

Milestone 12 keeps these boundaries unchanged. The final portfolio evidence links documentation,
quality gates, and Azure target-state mapping, but it does not add runtime functionality,
deployment automation, credentials, or live integrations.
