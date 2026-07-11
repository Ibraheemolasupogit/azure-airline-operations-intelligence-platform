# Capability Matrix

| Capability | Business problem addressed | Local implementation component | Azure target-state service | Generated evidence | Milestone | Interview value |
| --- | --- | --- | --- | --- | --- | --- |
| Synthetic data generation | Need safe data for demos and tests | `data_generation` package | Event Hubs and ADLS Gen2 landing zones | seven datasets, manifest, data dictionary | 2 | Shows reproducibility and synthetic-data governance. |
| Ingestion and validation | Need trusted inputs before analytics | `ingestion` and `validation` packages | Data Factory, ADLS Gen2, Purview | validation reports, processed data, quarantine | 3 | Shows contracts, quality controls, and lineage. |
| Forecasting | Need demand outlook by route/date | `forecasting` package | Azure Machine Learning | forecasts, metrics, model card | 4 | Shows leakage-aware modelling and evidence. |
| Classification | Need delay-risk signal | `delay_prediction` package | Azure Machine Learning | risk outputs, thresholds, metrics | 5 | Shows deterministic classifier governance. |
| Maintenance analytics | Need synthetic aircraft-health risk evidence | `maintenance` package | Azure Machine Learning, Azure Monitor | health scores, alerts, aircraft summaries | 6 | Shows decision-support boundaries for sensitive domains. |
| Disruption scoring | Need prioritised disruption severity | `disruption` package | Azure Functions, Azure Data Explorer | severity scores, drivers, alerts | 7 | Shows explainable operational scoring. |
| Monitoring | Need evidence that artefacts remain healthy | `monitoring` package | Azure Monitor, Log Analytics, Application Insights | metrics, checks, alerts, drift-style summary | 8 | Shows local observability discipline. |
| GenAI-style assistant | Need grounded operational narrative | `genai` package | Azure AI Foundry, Azure OpenAI, Content Safety | retrieved evidence, guardrails, transcript | 9 | Shows safe assistant design without live calls. |
| Dashboard exports | Need BI-ready consumption layer | `dashboard` and `reporting` packages | Power BI and Microsoft Fabric Lakehouse | star schema, KPI CSVs, semantic guidance | 10 | Shows dimensional modelling and BI handoff. |
| Azure architecture mapping | Need cloud target-state clarity | docs, `configs/azure_mapping.yaml`, `infra` | Azure platform services | architecture evidence and static checks | 11 | Shows cloud architecture thinking without deployment. |
| Security and governance | Need boundaries, lineage, and controls | docs, validators, `.gitignore` | Purview, Entra ID, Key Vault | governance docs, no-secret checks | 1-12 | Shows responsible handling of sensitive claims. |
| CI/CD and quality | Need repeatable local and CI validation | Makefile, tests, GitHub Actions | GitHub Actions local CI | full quality gate output | 1-12 | Shows engineering discipline and reviewability. |
