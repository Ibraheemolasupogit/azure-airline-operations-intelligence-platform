# Data Generation

Milestone 2 provides a local, deterministic synthetic aviation data generator.

## Configurations

- `configs/data_generation.yaml`: development profile.
- `configs/data_generation_ci.yaml`: small CI profile used by tests and the quality gate.

Configuration values are validated for dates, positive counts, probabilities, duplicate airport
codes, duplicate aircraft IDs, route airport references, supported aircraft types, seating
capacity, sensor ranges, and output-root boundaries.

## Generate Data

```bash
python3 -m airline_operations_intelligence.cli generate-data \
  --config configs/data_generation.yaml
```

Useful overrides:

```bash
python3 -m airline_operations_intelligence.cli generate-data \
  --config configs/data_generation_ci.yaml \
  --run-id ci-example \
  --seed 99 \
  --overwrite
```

`--output-root` may override the configured output root, but it must remain under `data/raw`.
Existing run directories are rejected unless `--overwrite` is supplied. Overwrite replaces the
complete run directory instead of mixing old and new files.

## Describe A Completed Run

```bash
python3 -m airline_operations_intelligence.cli describe-generation \
  --run-dir data/raw/<run_id>
```

This command reads `generation-manifest.json` and does not regenerate data.

## Output Structure

```text
data/raw/<run_id>/
├── flight_schedule.csv
├── passenger_demand.csv
├── weather_events.csv
├── aircraft_health.jsonl
├── crew_operations.csv
├── delay_history.csv
├── airport_events.jsonl
├── generation-manifest.json
├── data-dictionary.json
└── generation-summary.md
```

Normal generated runs are ignored by git.

## Quality Commands

```bash
make test-data-generation
make generate-data-ci
make quality
```

The full quality gate includes deterministic CI-profile generation.

## Known Limitations

Generation invariants are intentionally lightweight and are not a replacement for Milestone 3
governed ingestion and validation. The data is realistic enough for platform development but does
not represent certified aviation thresholds, real operating procedures, or legal compliance.
