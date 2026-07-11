# Azure Data Zone Mapping

| Local path | Target zone | Azure service | Container or table area |
| --- | --- | --- | --- |
| `data/raw` | Raw landing | ADLS Gen2 | `raw` |
| `data/interim` | Quarantine and interim | ADLS Gen2 | `interim` |
| `data/processed` | Curated operational | ADLS Gen2 | `processed` |
| `outputs` | Analytics and model evidence | ADLS Gen2 | `analytics` |
| `reports` | Governed evidence and reports | ADLS Gen2 | `evidence` |
| `dashboard/outputs` | Dashboard curated tables | Fabric Lakehouse or Power BI | `dashboard` |

Lineage is preserved through run IDs, manifests, checksums, report artefacts, and future Purview
entities. Each zone should have separate RBAC assignments and retention policies.
