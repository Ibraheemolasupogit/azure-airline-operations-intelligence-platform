# Azure Architecture Review

Use this local review command:

```bash
make validate-azure-architecture
```

The command checks architecture documents, diagrams, mapping configuration, reference templates,
non-deployment flags, required service mappings, and static safety patterns. It does not contact
Azure, does not require credentials, and does not execute infrastructure tooling.
