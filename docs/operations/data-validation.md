# Data Validation

Milestone 3 validates a completed Milestone 2 generation run.

## Run Validation

```bash
python3 -m airline_operations_intelligence.cli validate-data \
  --source-run-dir data/raw/<run_id> \
  --config configs/validation.yaml
```

Useful overrides:

```bash
python3 -m airline_operations_intelligence.cli validate-data \
  --source-run-dir data/raw/ci-quality \
  --config configs/validation_ci.yaml \
  --validation-run-id ci-quality \
  --overwrite
```

Validation does not regenerate source data. It requires a completed generation run containing the
seven required datasets plus `generation-manifest.json`, `data-dictionary.json`, and
`generation-summary.md`.

## Describe A Completed Run

```bash
python3 -m airline_operations_intelligence.cli describe-validation \
  --report-dir reports/validation/<validation_run_id>
```

This command reads `validation-manifest.json` and does not rerun validation.

## Outputs

```text
data/interim/<validation_run_id>/
├── normalized/
└── quarantine/
data/processed/<validation_run_id>/
reports/validation/<validation_run_id>/
├── validation-manifest.json
├── validation-results.json
├── quality-metrics.csv
├── lineage.json
└── validation-summary.md
```

## Quality Commands

```bash
make validate-data-ci
make test-ingestion-validation
make describe-validation-ci
make quality
```

Generated validation outputs are local artefacts and must not be committed.
