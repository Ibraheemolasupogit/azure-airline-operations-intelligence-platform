# Synthetic Data Governance

Milestone 2 generated data is fictional and intended for local development, CI, and future
architecture demonstrations.

## Controls

- No personal passenger data, booking references, contact details, loyalty identifiers, employee
  names, employee IDs, demographics, real aircraft defects, or real incident details are generated.
- Airport and aircraft identifiers are synthetic or generic references configured in YAML.
- Operational notes for airport events use fixed templates rather than ungoverned free text.
- The data dictionary marks every generated field as not containing personal data.
- Manifests include a synthetic-data declaration and known limitations.
- Generated run outputs under `data/raw/` are ignored by git.

## Boundaries

The data supports analytics and decision-support demonstrations only. Sensor ranges, risk scores,
crew operations, delay causes, cancellations, diversions, and disruption patterns are illustrative.
They are not certified aviation thresholds, airworthiness evidence, legal crew compliance evidence,
or operational instructions.

## Traceability

Each run writes:

- `generation-manifest.json` with configuration snapshot, fingerprint, row counts, checksums,
  fields, keys, counts, warnings, and limitations.
- `data-dictionary.json` with field-level definitions and classifications.
- `generation-summary.md` with human-readable run metadata and operational counts.

These artefacts provide lineage input for later Milestone 3 validation and governance work.
