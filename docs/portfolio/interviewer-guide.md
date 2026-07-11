# Interviewer Guide

## Ten-Minute Review

1. Read the [README](../../README.md) summary and boundaries.
2. Open the [capability matrix](capability-matrix.md) to see business value and Azure mapping.
3. Review the [milestone evidence index](milestone-evidence-index.md) for the implemented path.
4. Skim the [final architecture narrative](../architecture/final-platform-architecture.md).
5. Check the [final repository health report](../../reports/architecture/final-repository-health.md).

## Thirty-Minute Review

1. Run `make quality` locally.
2. Inspect `configs/*_ci.yaml` to see deterministic CI-sized profiles.
3. Review integration tests under `tests/integration`.
4. Inspect `docs/governance` for responsible-use boundaries.
5. Inspect `docs/azure` and `infra/README.md` for target-state and non-deployment controls.
6. Review final diagrams under `diagrams/final-*.mmd`.

## Run The Local Quality Gate

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make quality
```

`make quality` runs local checks and a CI-sized generation flow, then removes generated outputs.

## Inspect The Architecture

Start with [final platform architecture](../architecture/final-platform-architecture.md), then
review:

- [target architecture](../architecture/target-architecture.md);
- [domain boundaries](../architecture/domain-boundaries.md);
- [Azure target architecture](../azure/azure-target-architecture.md);
- [Azure service mapping](../azure/azure-service-mapping.md);
- [final platform flow diagram](../../diagrams/final-platform-flow.mmd).

## Inspect Evidence Outputs Without Committing Artefacts

Run a command with a unique run ID, inspect `data/`, `outputs/`, `dashboard/outputs/`, and
`reports/`, then run `make clean` or remove the run-specific ignored folders. Confirm hygiene with:

```bash
git status --short --ignored
```

Only source, docs, tests, configs, and committed architecture reports should be considered for
commit.

## Likely Questions And Evidence Points

| Question | Evidence point |
| --- | --- |
| How is reproducibility handled? | Deterministic configs, run IDs, manifests, checksums, and tests. |
| How is data quality handled? | Validation rules, quarantine outputs, reports, and lineage. |
| How is ML risk controlled? | Baselines, partitions, model cards, metrics, and no automated decisions. |
| How is GenAI bounded? | Local templates, evidence citations, guardrails, and no live LLM calls. |
| How does this map to Azure? | `configs/azure_mapping.yaml`, `docs/azure`, and reference-only `infra/`. |
| How do you prevent generated artefacts in git? | `.gitignore`, `make clean`, quality cleanup, and readiness validation. |

## Azure Mapping Explanation

The project maps data ingestion to Event Hubs and Data Factory, lake zones to ADLS Gen2, modelling
to Azure Machine Learning, assistant patterns to Azure AI Foundry, observability to Azure Monitor,
governance to Microsoft Purview, dashboards to Power BI, and identity/secrets to Entra ID and Key
Vault. This is target-state documentation only.

## Synthetic Data And Safety Boundaries

The synthetic datasets are fictional and locally generated. They do not represent real passengers,
crew, aircraft defects, airport incidents, airline schedules, or regulated operational facts. All
analytics are demonstration artefacts requiring human review.

## Limitations And Future Work

The repository does not deploy to Azure, publish dashboards, call live LLMs, process real-time
streams, or make operational decisions. Future work could add reviewed deployment, secured
configuration, managed orchestration, and richer BI assets as separate milestones.
