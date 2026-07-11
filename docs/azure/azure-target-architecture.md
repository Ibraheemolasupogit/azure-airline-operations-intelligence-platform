# Azure Target Architecture

Milestone 11 defines a target-state Azure architecture for the local-first airline operations
intelligence platform. It is reference-only architecture guidance and does not provision cloud
resources.

## Architecture Layers

- Ingestion: Azure Event Hubs for streaming aviation events, Azure Data Factory or Fabric Data
  Factory for scheduled ingestion, Azure Functions for lightweight control checks, and ADLS Gen2
  raw landing storage.
- Storage: ADLS Gen2 zones for raw, interim, processed, analytics, and evidence data, with Fabric
  Lakehouse or Warehouse as a future dashboard consumption layer.
- Validation: Data Factory or Fabric pipelines invoking reusable validation jobs with quarantine
  storage, manifest checks, and Log Analytics evidence.
- Analytics and ML: Azure Machine Learning batch jobs for passenger forecasting, delay prediction,
  aircraft-health analytics, and disruption scoring.
- Monitoring: Azure Monitor, Log Analytics, Application Insights, and Azure Data Explorer for
  telemetry, metrics, query evidence, and human-review alerts.
- GenAI: Azure AI Foundry, Azure OpenAI, Prompt Flow, Azure AI Content Safety, Key Vault, and
  managed identities as future implementation boundaries.
- Dashboards: Fabric Lakehouse or Warehouse and Power BI semantic models consuming governed
  dashboard exports from Milestone 10.
- Governance: Microsoft Entra ID, managed identities, RBAC, private endpoints, Key Vault,
  Purview lineage, retention, audit logging, responsible AI, and aviation safety boundaries.

## Non-Deployment Statement

This repository contains local synthetic workflows, documentation, static validation, and
reference templates only. It does not create Azure resources, publish Power BI content, or call
cloud APIs.
