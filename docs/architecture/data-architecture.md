# Data Architecture

Milestone 2 generates synthetic source datasets under `data/raw/<run_id>/`. The datasets must not
represent real passengers, employees, aircraft defects, or confidential airline operations.

| Source | Purpose | Grain | Representative fields | Relationships | Classification | Validation controls | Consumers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `flight_schedule.csv` | Planned flight operations context | One row per scheduled flight leg | flight_id, route, origin, destination, scheduled_departure, aircraft_type | Joins to demand, delay history, crew, events | Synthetic operational | Required keys, timestamp validity, route code checks | Delay prediction, disruption scoring, reporting |
| `passenger_demand.csv` | Demand by route and departure period | Route-period demand record | route, departure_date, cabin, bookings, load_factor | Joins to schedule by route and date | Synthetic commercial aggregate | Non-negative counts, valid periods, load-factor range | Forecasting, executive reporting |
| `weather_events.csv` | Weather conditions affecting operations | Airport-time weather observation | airport, event_time, condition, severity, wind_speed | Joins to flights by airport and time window | Synthetic environmental | Valid severity, time window checks, airport code checks | Delay prediction, anomaly detection |
| `aircraft_health.jsonl` | Aircraft telemetry indicators | Aircraft-time indicator event | aircraft_id, event_time, sensor_name, value, threshold | Joins to schedule by aircraft and time | Synthetic maintenance | Numeric range checks, known sensors, missing-rate checks | Maintenance analytics, monitoring |
| `crew_operations.csv` | Crew assignment and readiness context | Crew pairing or flight assignment | crew_pairing_id, flight_id, duty_start, duty_end, status | Joins to schedule by flight_id | Synthetic operational | Duty timestamp order, status domain checks | Disruption scoring |
| `delay_history.csv` | Historical delay outcomes and causes | One row per historical flight outcome | flight_id, actual_departure, delay_minutes, cause_code | Joins to schedule by flight_id | Synthetic operational | Delay range checks, cause-code checks, no future leakage | Delay prediction, route analysis |
| `airport_events.jsonl` | Airport constraints and operational events | Airport-time event | airport, event_time, event_type, severity, expected_duration | Joins to schedule and weather by airport and time | Synthetic operational | Event taxonomy checks, duration checks | Disruption scoring, monitoring |

## Data Zones

- `data/raw`: immutable synthetic source landings in future milestones.
- `data/interim`: validated but not final transformation outputs.
- `data/processed`: curated operational datasets ready for analytics.

Generated records in all zones are ignored by git except `.gitkeep` placeholders. Each synthetic
raw run also includes `generation-manifest.json`, `data-dictionary.json`, and
`generation-summary.md`.

See [synthetic data architecture](synthetic-data-architecture.md) for generation design,
relationships, deterministic behaviour, and Azure mapping.
