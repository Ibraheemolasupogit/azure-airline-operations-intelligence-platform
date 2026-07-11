# Azure Deployment Architecture

The Azure deployment architecture is a target-state map for future deployment work. It connects
the implemented local capabilities from Milestones 1 through 10 to Azure services while preserving
the current repository boundary: local, deterministic, synthetic-data-only, and non-deploying.

The architecture uses ADLS Gen2 data zones, Azure Data Factory or Fabric Data Factory ingestion,
Azure Machine Learning batch analytics, Azure Monitor and Log Analytics observability, Azure AI
Foundry assistant governance, Power BI and Fabric dashboard consumption, Microsoft Purview
lineage, Key Vault, managed identities, RBAC, and private networking.

Reference templates in `infra/` are examples for architecture review only.
