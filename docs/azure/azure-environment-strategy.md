# Azure Environment Strategy

The target architecture separates `dev`, `test`, and `prod`.

| Environment | Purpose | Data | Controls |
| --- | --- | --- | --- |
| dev | Architecture iteration and local parity | Synthetic only | Lowest cost, short retention, no production access. |
| test | Release validation and integration rehearsal | Synthetic or approved masked data in future | Stronger RBAC and diagnostic coverage. |
| prod | Future governed production boundary | Not implemented | Private networking, formal approvals, retention, and audit. |

Resource groups follow `rg-aoi-{environment}-{region}` with default region `uksouth`. Naming uses
the `aoi` workload prefix plus environment and service purpose.

The current repository remains local and deterministic. Environment names are configuration
metadata only.
