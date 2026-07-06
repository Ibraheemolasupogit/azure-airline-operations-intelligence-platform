# Flight-Delay Prediction Architecture

Milestone 5 adds local, deterministic flight-delay prediction on top of completed Milestone 3
validation evidence.

## Inputs

- Required explicit validation report directory containing `validation-manifest.json` and
  `lineage.json`.
- Required processed datasets: flight schedule, delay history, weather events, airport events,
  crew operations, aircraft health, and passenger demand.
- Optional passenger forecast report from Milestone 4, only when it traces to the same validation
  run and only forecast columns are consumed.

## Modelling Grain

The modelling grain is one prediction per scheduled flight. Cancelled flights are excluded by
default. Diverted flights remain eligible only when they have a valid departure record.

## Cutoff And Leakage Controls

The default prediction cutoff is 120 minutes before scheduled departure. Features are limited to
schedule attributes, pre-cutoff weather and airport events, pre-cutoff crew state, pre-cutoff
aircraft telemetry, optional forecast values, and historical aggregates built from prior flights
only.

Actual departure and arrival timestamps, delay outcomes, delay causes, taxi and airborne fields,
reactionary delay, cancellation and diversion outcomes, post-cutoff telemetry, and full-dataset
target aggregates are prohibited model features.

## Training Flow

1. Verify validation manifest status, row counts, and processed checksums.
2. Build leakage-safe flight-level features.
3. Split chronologically into train, validation, and test partitions.
4. Train majority-class and route-history baselines plus a deterministic logistic candidate.
5. Select the champion and probability threshold using validation metrics.
6. Evaluate the champion on the test partition.
7. Write predictions, metrics, model artefacts, reports, manifest, and lineage.

## Outputs

Outputs are written under `outputs/delay_prediction`, `outputs/models/delay_prediction`, and
`reports/delay_prediction`. Generated artefacts are ignored by git.
