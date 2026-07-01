# Data Quality Governance

Milestone 3 separates lightweight generation invariants from governed validation. Generation
invariants prevent obvious corrupt synthetic outputs. Governed validation creates auditable
evidence before data is considered curated.

## Severity Policy

- `fatal`: source-integrity failures that make validation unsafe, such as unreadable manifests,
  unsupported manifest versions, missing required files, unsafe paths, or checksum mismatches.
- `error`: invalid record or dataset conditions such as duplicate primary keys, broken foreign
  keys, invalid timestamp ordering, impossible values, or failed required business rules.
- `warning`: unusual but technically accepted conditions, such as minor metric discrepancies or
  unusual operational patterns.
- `info`: informational evidence and successful aggregate metrics.

By default, validation fails on fatal findings and errors, but not warnings.

## Quarantine Policy

Record-level errors are quarantined when quarantine is enabled. Quarantine records preserve the
source record, row number, primary identifier, failed rule IDs, severities, messages, source run ID,
and validation run ID. Valid records remain in processed outputs.

Dataset-level and source-integrity failures are reported even when no individual record can be
quarantined.

## Evidence

Each validation run writes:

- `validation-manifest.json` with counts, checksums, rules, configuration, and status.
- `validation-results.json` with all failed rule results and successful-record aggregates.
- `quality-metrics.csv` with dataset-level quality dimensions.
- `lineage.json` with source, processed, quarantine, and report artefacts.
- `validation-summary.md` generated from actual run results.

These artefacts are candidates for future Microsoft Purview, Azure Monitor, Log Analytics, and
Power BI integration. No live Azure integration is implemented in Milestone 3.
