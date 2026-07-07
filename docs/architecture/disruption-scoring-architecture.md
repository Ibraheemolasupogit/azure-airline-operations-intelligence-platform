# Disruption Scoring Architecture

Milestone 7 adds deterministic local operational disruption scoring from completed Milestone 3
validation evidence, with optional compatible outputs from Milestones 4, 5, and 6.

## Inputs

- Required processed schedule, delay, weather, airport-event, crew, aircraft-health, and
  passenger-demand datasets from a named validation run.
- Optional passenger forecast outputs.
- Optional flight-delay prediction outputs.
- Optional aircraft-health maintenance analytics outputs.

## Scoring Flow

1. Verify validation manifests, row counts, required fields, and checksums.
2. Verify optional upstream analytics manifests and checksums when supplied.
3. Build one disruption feature row per scheduled flight.
4. Separate retrospective outcome context from forward-looking risk evidence.
5. Score delay, weather, airport-event, crew, aircraft-health, passenger-pressure, and network
   reactionary components.
6. Produce forward risk, retrospective severity, and overall disruption severity.
7. Assign risk bands and recovery-priority categories.
8. Generate conservative alerts, summaries, metrics, lineage, manifest, and reports.

## Boundary

This workflow is synthetic decision-support analytics only. It is not operations-control software,
air-traffic-control tooling, autonomous recovery optimisation, dispatch authority, passenger-care
automation, or safety-critical decision software.
