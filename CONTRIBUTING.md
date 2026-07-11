# Contributing

## Workflow

1. Create a focused branch from the current main branch.
2. Keep changes scoped to the active milestone.
3. Do not commit credentials, generated datasets, model artefacts, cloud state, or regenerated
   reports.
4. Run the local quality gate before opening a pull request:

```bash
make quality
```

## Development Standards

- Use the `src/` package layout and keep domain boundaries explicit.
- Prefer typed, deterministic utilities with clear docstrings.
- Add tests for behaviour, not placeholder assertions.
- Keep configuration non-secret and environment-neutral.
- Document architecture decisions when adding new platform capabilities.

## Milestone Discipline

Keep changes scoped to the active roadmap milestone. Milestone 11 adds Azure target-state
architecture mapping and reference-only infrastructure skeletons only; do not add route or
schedule optimisation, live Azure deployment workflows, Azure SDK clients, Power BI or Fabric
publishing clients, OpenAI or Azure OpenAI SDKs, alert routing, production incident automation, or
Milestone 12 portfolio polish until their roadmap milestone is active.

Generated runs under `data/raw/`, `data/interim/`, `data/processed/`, and `reports/validation/`
plus analytics, monitoring, and assistant outputs under `outputs/` and `reports/` are local
artefacts and must not be committed. Generated dashboard outputs under `dashboard/outputs/` and
`reports/dashboard_outputs/` are also ignored runtime artefacts.

Run `make validate-azure-architecture` when changing Azure architecture docs, mapping config, or
reference infrastructure skeletons.
