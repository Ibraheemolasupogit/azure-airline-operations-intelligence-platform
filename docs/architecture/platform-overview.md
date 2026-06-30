# Platform Overview

## Business Objectives

The platform will demonstrate how a governed airline operations intelligence environment can
support an operations control centre. It will combine planned operational context, synthetic
event streams, curated analytical datasets, machine-learning evidence, monitoring, reporting,
and future GenAI assistance.

Expected decision areas include delay-risk triage, passenger-demand planning, aircraft-health
monitoring, anomaly investigation, disruption severity assessment, network-impact analysis,
recovery prioritisation, and executive reporting.

## Users

Target users include network operations controllers, airport operations teams, crew operations
teams, engineering and maintenance teams, commercial planning teams, customer disruption teams,
data scientists, data engineers, and operational executives.

## Local-First Design

Development remains runnable locally using synthetic data. Azure services are represented in
Milestone 1 through interfaces, configuration, diagrams, documentation, and package boundaries.
No Azure subscription or cloud credentials are required.

## Azure Production Mapping

Local producers map to Azure Event Hubs, local landing zones map to Azure Data Lake Storage
Gen2, validation and stream-processing boundaries map to Azure Stream Analytics and data-quality
controls, analytical serving maps to Synapse Analytics and Azure Data Explorer, ML maps to Azure
Machine Learning, GenAI maps to Azure AI Foundry, reporting maps to Power BI, and governance maps
to Microsoft Purview, Entra ID, Key Vault, Azure Monitor, and Application Insights.

## Batch And Streaming Paths

The intended batch path starts with synthetic schedules, demand, history, and maintenance files
landing in a raw zone before validation, curation, feature generation, modelling, and reporting.
The intended streaming path starts with synthetic operational events, maps to Event Hubs, and
feeds validation, anomaly, telemetry, and disruption-scoring services.

## Analytical Consumption

Future consumers will include curated datasets, operational outputs, model evidence, Power BI
semantic models, reports, monitoring views, and grounded GenAI responses. Consumers should use
published contracts rather than importing internal domain implementation details.

## MVP Non-Goals

Milestone 1 does not implement data generation, data ingestion, forecasting, prediction,
maintenance analytics, disruption scoring, dashboards, GenAI runtimes, Azure resources, or
infrastructure-as-code deployments.
