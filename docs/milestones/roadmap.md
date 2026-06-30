# Roadmap

| Milestone | Objective | Principal deliverables | Acceptance criteria | Dependencies |
| --- | --- | --- | --- | --- |
| 1 - Repository foundation and architecture baseline | Establish structure, docs, config, tests, quality tooling, and CI | Package layout, validation CLI, architecture docs, governance docs | Full local quality gate passes; no later functionality implemented | None |
| 2 - Synthetic aviation data generation | Produce deterministic synthetic source data | Data generator contracts, synthetic files, data dictionary | Generated data is reproducible and clearly synthetic | 1 |
| 3 - Governed ingestion and validation | Land and validate synthetic data | Ingestion interfaces, validation rules, quality reports | Invalid records are rejected and lineage is captured | 2 |
| 4 - Passenger-demand forecasting | Forecast route-period demand | Baselines, forecasting models, evaluation artefacts | Chronological validation demonstrates performance against baselines | 3 |
| 5 - Flight-delay prediction | Estimate delay risk | Delay features, baseline and tree models, risk outputs | Leakage checks and operational metrics pass | 3 |
| 6 - Aircraft-health and maintenance analytics | Analyse synthetic health indicators | Anomaly and risk scoring evidence | Outputs remain decision-support and not airworthiness claims | 3 |
| 7 - Operational disruption scoring | Quantify disruption severity | Scoring logic, impact evidence, recovery context | Scores are explainable and traceable to inputs | 4, 5, 6 |
| 8 - Monitoring and observability | Add platform telemetry | Logs, metrics, data-quality monitoring, health checks | Local monitoring evidence exists | 3 |
| 9 - GenAI operations assistant | Add grounded assistant workflows | Retrieval contracts, prompts, audit logs, response checks | Responses cite evidence and require human review | 7, 8 |
| 10 - Power BI-ready analytical outputs | Publish reporting artefacts | Star-schema outputs, semantic model guidance, reports | Outputs are reproducible and documented | 7 |
| 11 - Azure deployment architecture and infrastructure mapping | Prepare deployable Azure architecture | IaC boundaries, deployment docs, security mapping | No secrets committed; deployment plan is auditable | 8, 10 |
| 12 - Portfolio evidence and final polish | Package final demonstration evidence | Final docs, screenshots, quality evidence, narrative | Claims match implemented evidence | 1-11 |
