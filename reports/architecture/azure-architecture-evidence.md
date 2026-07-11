# Azure Architecture Evidence

Milestone 11 architecture evidence is static and committed as documentation.

## Evidence Summary

- Required Azure architecture documents are present under `docs/azure/`.
- Required diagrams are present under `diagrams/`.
- Local paths are mapped to ADLS Gen2, Fabric, and Power BI target zones.
- Azure services are mapped for ingestion, storage, validation, ML, monitoring, GenAI, dashboard,
  governance, identity, and networking.
- Security controls cover Entra ID, managed identities, RBAC, Key Vault, private endpoints,
  logging, retention, and synthetic-data boundaries.
- Governance controls cover Purview lineage, classification, retention, responsible AI, and
  aviation safety disclaimers.
- Deployment safety policy is reference-only with deployment disabled.
- No live cloud resources are created by Milestone 11.

## Known Limitations

The evidence is architecture documentation, not an operational deployment assessment. Future cloud
implementation requires security review, environment approval, cost modelling, and production
readiness work.
