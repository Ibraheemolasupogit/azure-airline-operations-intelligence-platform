# Azure Monitoring And Observability

Milestone 8 local monitoring maps to Azure Monitor, Log Analytics, Application Insights, and
Azure Data Explorer.

| Local artefact | Azure mapping |
| --- | --- |
| `monitoring-metrics.csv` | Log Analytics custom metrics table. |
| `monitoring-checks.jsonl` | Custom check evidence table. |
| `monitoring-alerts.jsonl` | Scheduled query rule evidence and human-review queue. |
| `platform-health-summary.csv` | Dashboard and operational health summary. |
| `drift-comparison.csv` | Drift-style analytics in Log Analytics or Data Explorer. |

Alerts are advisory and require human review. They are not autonomous incident remediation.
