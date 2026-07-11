# Azure Security And Governance

Target-state security uses Microsoft Entra ID, managed identities, RBAC, Key Vault, private
endpoints, network isolation, diagnostic logging, Microsoft Purview, and human-review controls.

## Controls

- Identity: managed identities for services and Entra groups for personas.
- Access: least-privilege RBAC per environment, data zone, and service boundary.
- Secrets: Key Vault in future runtime; no secrets in repository files.
- Network: private endpoints and restricted public access in production target state.
- Audit: diagnostic settings to Log Analytics and retained evidence reports.
- Governance: Purview collections for data assets, classification, lineage, and retention.
- Responsible AI: model cards, guardrail results, prompt audit, and mandatory human review.
- Aviation boundary: outputs are decision-support evidence, not operational command systems.
