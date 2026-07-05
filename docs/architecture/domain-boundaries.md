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

Will answer operational questions from governed outputs, cite evidence, distinguish facts from
recommendations, and avoid autonomous operational action.

## Monitoring

Will collect pipeline, data-quality, model, and application telemetry with local logs and an
Azure Monitor and Application Insights target mapping.

## Reporting

Will produce operational reports and Power BI-ready outputs from curated datasets and model
evidence, not from raw or private implementation details.
