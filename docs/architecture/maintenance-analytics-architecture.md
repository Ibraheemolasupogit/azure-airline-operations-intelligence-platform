# Maintenance Analytics Architecture

Milestone 6 adds local, deterministic aircraft-health and maintenance-risk analytics on top of
completed Milestone 3 validation evidence.

## Inputs

- Required validation report directory containing `validation-manifest.json` and `lineage.json`.
- Required processed datasets: `aircraft_health.jsonl`, `flight_schedule.csv`, and
  `delay_history.csv`.
- Supporting datasets may be verified when present: crew operations, weather events, airport
  events, and passenger demand.

## Analytics Flow

1. Verify validation status, manifest version, row counts, checksums, and required fields.
2. Build aircraft-health features from telemetry, utilisation, fault-code, trend, and
   retrospective operational context.
3. Calculate deterministic component scores for sensor thresholds, telemetry anomalies,
   degradation trend, fault-code evidence, utilisation, and recent operational context.
4. Combine component scores with configured weights.
5. Assign maintenance-risk score, aircraft-health score, risk band, and alert category.
6. Generate conservative alerts that require human review.
7. Write features, scores, alerts, summaries, metrics, manifest, lineage, and reports.

## Boundaries

The workflow is decision-support analytics over synthetic data. It is not certified predictive
maintenance, airworthiness evidence, dispatch control, a maintenance-control system, or a safety
diagnostic system.

## Future Azure Mapping

The local flow can later map to ADLS Gen2 or Azure Data Explorer for curated telemetry, Azure
Machine Learning or batch analytics jobs for feature preparation, Azure Monitor or Logic Apps for
alert routing, and Microsoft Purview for lineage. Milestone 6 deploys none of those services.
