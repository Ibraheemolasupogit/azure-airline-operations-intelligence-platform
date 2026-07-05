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

Milestone 4 adds passenger-demand forecasting only. Do not add flight-delay prediction,
maintenance models, disruption scoring, optimisation, dashboards, Azure deployment templates,
production monitoring, or GenAI runtime features until their roadmap milestone is active.

Generated runs under `data/raw/`, `data/interim/`, `data/processed/`, and `reports/validation/`
plus passenger forecasting outputs under `outputs/` and `reports/passenger_forecasting/` are local
artefacts and must not be committed.
