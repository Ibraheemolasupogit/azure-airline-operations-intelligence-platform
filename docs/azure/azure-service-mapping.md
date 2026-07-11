# Azure Service Mapping

| Local capability | Milestone | Target Azure mapping | Notes |
| --- | --- | --- | --- |
| Repository quality gate | 1 | GitHub Actions local CI | No Azure login or deployment job. |
| Synthetic generation | 2 | Event Hubs, Data Factory, ADLS Gen2 raw | Synthetic sources remain non-production evidence. |
| Ingestion and validation | 3 | Data Factory, Fabric pipelines, ADLS quarantine, Purview | Manifest and checksum checks map to lineage controls. |
| Passenger forecasting | 4 | Azure Machine Learning batch job | Model artefacts map to AML evidence storage. |
| Delay prediction | 5 | Azure Machine Learning batch scoring | Cutoff and leakage controls map to responsible ML evidence. |
| Maintenance analytics | 6 | Azure Machine Learning deterministic scoring | Decision-support only, not airworthiness evidence. |
| Disruption scoring | 7 | Azure Machine Learning batch scoring | Recovery-priority evidence requires human review. |
| Monitoring | 8 | Azure Monitor, Log Analytics, Application Insights, Data Explorer | Local monitoring outputs map to custom tables and alerts. |
| GenAI assistant | 9 | Azure AI Foundry, Azure OpenAI, Prompt Flow, Content Safety | Future grounded assistant only, with audit and guardrails. |
| Dashboard outputs | 10 | Power BI, Fabric Lakehouse, Fabric Warehouse | Local exports inform future semantic models and reports. |

All mappings are target-state architecture documentation. No live service integration is
implemented in Milestone 11.
