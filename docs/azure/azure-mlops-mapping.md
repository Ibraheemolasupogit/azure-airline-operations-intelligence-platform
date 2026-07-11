# Azure MLOps Mapping

Milestones 4 through 7 map to Azure Machine Learning as batch, evidence-driven jobs.

| Local workflow | Azure ML mapping | Evidence |
| --- | --- | --- |
| Passenger forecasting | AML job and model registry candidate | Forecasts, metrics, model card, lineage. |
| Delay prediction | AML batch scoring and candidate comparison | Thresholds, leakage checks, calibration, metrics. |
| Maintenance analytics | AML deterministic scoring job | Risk features, scores, alerts, safety disclaimers. |
| Disruption scoring | AML batch scoring job | Component scores, recovery priority, human-review flags. |

The target design keeps model approval separate from scoring. Production use would require
registered data assets, reviewed environments, managed identities, model governance, monitoring,
and rollback procedures.
