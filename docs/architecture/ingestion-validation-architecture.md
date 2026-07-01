# Ingestion And Validation Architecture

Milestone 3 adds a governed local ingestion and validation workflow for completed Milestone 2
generation runs. It does not regenerate source data and does not deploy Azure resources.

## Flow

```mermaid
flowchart TD
    raw["data/raw/<run_id><br/>Milestone 2 generation run"]
    manifest["Manifest and checksum verification"]
    parse["Parsing and conservative normalization"]
    schema["Schema validation"]
    business["Business-rule validation"]
    relationships["Cross-dataset relationship validation"]
    processed["data/processed/<validation_run_id><br/>curated valid records"]
    quarantine["data/interim/<validation_run_id>/quarantine<br/>invalid records with reasons"]
    reports["reports/validation/<validation_run_id><br/>manifest, results, metrics, lineage"]

    raw --> manifest --> parse --> schema --> business --> relationships
    relationships --> processed
    relationships --> quarantine
    relationships --> reports

    raw -. future .-> adls["ADLS Gen2 landing zone"]
    manifest -. future .-> control["Ingestion-control metadata<br/>Azure Functions or Data Factory checks"]
    parse -. future .-> factory["Data Factory, Synapse, Databricks, or Fabric"]
    business -. future .-> quality["Reusable governed data-quality jobs"]
    processed -. future .-> curated["ADLS curated zone and Synapse"]
    quarantine -. future .-> quarantineZone["ADLS quarantine zone"]
    reports -. future .-> purview["Microsoft Purview, Azure Monitor, Log Analytics"]
```

## Components

- Source discovery requires an explicit source run directory and verifies required artefacts.
- Manifest integrity checks validate source filenames, schema version, row counts, checksums, keys,
  formats, field lists, and safe paths.
- Readers parse CSV and JSON Lines with explicit UTF-8 handling.
- Normalization trims strings, parses timestamps to UTC, and parses numeric and boolean values
  without inventing defaults.
- Validation rules emit structured findings with stable rule identifiers, severities, categories,
  record identifiers, source rows, and quarantine eligibility.
- Outputs are written through temporary directories and promoted only after a complete run.

## Output Zones

- `data/interim/<validation_run_id>/normalized`: normalized valid records for audit.
- `data/interim/<validation_run_id>/quarantine`: invalid records with all failure reasons.
- `data/processed/<validation_run_id>`: curated valid records preserving the seven source names.
- `reports/validation/<validation_run_id>`: validation manifest, results, metrics, lineage, and
  summary.

Milestone 3 validation remains local-first and deterministic. Azure service mappings are
documented for later milestones only.
