# Final Local Validation Guide

## Environment Setup

Use Python 3.11 or later. Create and activate a local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Command

```bash
make install
```

This installs the package with development dependencies for linting, type checking, tests,
Markdown checks, and YAML checks.

## Quality Command

```bash
make quality
```

The quality gate is the preferred reviewer command. It runs local static checks, tests, static
repository validators, CI-sized generation and analytics, dashboard output generation, and cleanup.

## Selected Milestone Commands

```bash
make generate-data-ci
make validate-data-ci
make forecast-passenger-demand-ci
make predict-flight-delays-ci
make analyse-aircraft-health-ci
make score-disruptions-ci
make monitor-platform-ci
make run-operations-assistant-ci
make build-dashboard-outputs-ci
make validate-azure-architecture
make validate-portfolio-readiness
```

## Expected Cleanup Behaviour

`make quality` ends with `make clean`, which removes the CI run ID `ci-quality` from local data,
output, dashboard, and report directories. Development runs with other run IDs remain ignored by
git and should be removed manually when no longer needed.

## Where Outputs Are Generated

- `data/raw/<run_id>` for synthetic sources.
- `data/interim/<run_id>` and `data/processed/<run_id>` for validation zones.
- `outputs/<domain>/<run_id>` for analytical outputs.
- `outputs/models/<domain>/<run_id>` for local model evidence where applicable.
- `reports/<domain>/<run_id>` for runtime reports.
- `dashboard/outputs/<run_id>` for BI-ready CSV exports.
- `reports/architecture/*.md` for committed static architecture and portfolio evidence.

## Why Outputs Are Ignored By Git

Generated runtime artefacts are reproducible from configuration and can be large or run-specific.
Keeping them ignored prevents accidental commits of synthetic run outputs, logs, caches, and
environment-specific files. Static documentation evidence under `reports/architecture/` is the
exception and is intended for review.

## Confirm Repository Hygiene

```bash
git status --short --ignored
make clean
make validate-portfolio-readiness
```

After final cleanup, `git status --short` should show only intentional source, documentation,
test, config, workflow, or static report changes.

## Troubleshooting

- If Markdown checks fail, inspect the reported file and line from `pymarkdown`.
- If YAML checks fail, run `python3 -m yamllint .` for exact locations.
- If generated artefacts remain, run `make clean` and remove any non-`ci-quality` development run
  directories you created.
- If portfolio readiness fails, read each reported missing file, forbidden command, or generated
  artefact and fix the repository state rather than weakening the check.
