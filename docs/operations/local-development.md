# Local Development

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

## Validate The Repository

```bash
python3 -m airline_operations_intelligence.cli validate-repository
```

The validation command checks repository-level foundation conditions:

- Required directories exist.
- Expected baseline files exist.
- `configs/platform.yaml` loads and passes non-secret governance checks.
- Configured local paths exist.
- The package imports correctly.

It does not validate datasets, because Milestone 1 intentionally does not include datasets.

## Quality Gate

```bash
make quality
```

This runs Ruff lint and formatting checks, mypy, pytest, Markdown checks, YAML checks, and the
repository validation CLI.
