"""Milestone 2 dataset contracts used by Milestone 3 validation."""

from __future__ import annotations

from airline_operations_intelligence.validation.models import DatasetContract, FieldSpec

REQUIRED_DATASET_NAMES = (
    "flight_schedule.csv",
    "passenger_demand.csv",
    "weather_events.csv",
    "aircraft_health.jsonl",
    "crew_operations.csv",
    "delay_history.csv",
    "airport_events.jsonl",
)

SUPPORTED_AIRCRAFT_TYPES = frozenset({"A320", "A321", "B737-800", "B787-9", "E190"})
SERVICE_TYPES = frozenset({"scheduled"})
SCHEDULE_STATUSES = frozenset({"scheduled"})
WEATHER_TYPES = frozenset({"clear_wind", "rain", "thunderstorm", "fog", "snow"})
HEALTH_STATUSES = frozenset({"normal", "watch", "review"})
DEMAND_SEGMENTS = frozenset({"business-heavy", "leisure-heavy", "balanced"})
DELAY_CATEGORIES = frozenset({"early", "on_time", "minor", "moderate", "major"})
DELAY_CAUSES = frozenset({"weather", "airport", "crew", "aircraft", "reactionary", "airline_operations", "cancelled"})
AIRPORT_EVENT_TYPES = frozenset(
    {
        "runway_restriction",
        "terminal_congestion",
        "ground_handling_shortage",
        "air_traffic_flow_restriction",
        "security_incident_simulation",
        "equipment_outage",
        "deicing_constraint",
        "baggage_system_disruption",
    }
)
AIRPORT_EVENT_STATUSES = frozenset({"synthetic_active"})


def contracts_by_name() -> dict[str, DatasetContract]:
    """Return validation contracts keyed by dataset filename."""
    contracts = [
        DatasetContract(
            filename="flight_schedule.csv",
            file_format="csv",
            primary_key=("flight_id",),
            foreign_keys={
                "origin_airport": "airports.code",
                "destination_airport": "airports.code",
                "aircraft_id": "fleet.aircraft_id",
                "route_id": "routes.route_id",
            },
            fields=(
                FieldSpec("flight_id", "string"),
                FieldSpec("flight_number", "string"),
                FieldSpec("operating_date", "date"),
                FieldSpec("scheduled_departure_utc", "timestamp"),
                FieldSpec("scheduled_arrival_utc", "timestamp"),
                FieldSpec("origin_airport", "string"),
                FieldSpec("destination_airport", "string"),
                FieldSpec("route_id", "string"),
                FieldSpec("aircraft_id", "string"),
                FieldSpec("aircraft_type", "string", enum=SUPPORTED_AIRCRAFT_TYPES),
                FieldSpec("seat_capacity", "integer", minimum=1),
                FieldSpec("scheduled_block_minutes", "integer", minimum=1),
                FieldSpec("departure_terminal", "string"),
                FieldSpec("arrival_terminal", "string"),
                FieldSpec("service_type", "string", enum=SERVICE_TYPES),
                FieldSpec("schedule_status", "string", enum=SCHEDULE_STATUSES),
            ),
        ),
        DatasetContract(
            filename="passenger_demand.csv",
            file_format="csv",
            primary_key=("flight_id", "observation_date"),
            foreign_keys={"flight_id": "flight_schedule.flight_id", "route_id": "routes.route_id"},
            fields=(
                FieldSpec("flight_id", "string"),
                FieldSpec("observation_date", "date"),
                FieldSpec("days_before_departure", "integer", minimum=0),
                FieldSpec("route_id", "string"),
                FieldSpec("booked_passengers", "integer", minimum=0),
                FieldSpec("expected_final_passengers", "integer", minimum=0),
                FieldSpec("seat_capacity", "integer", minimum=1),
                FieldSpec("load_factor", "number", minimum=0),
                FieldSpec("booking_velocity", "number", minimum=0),
                FieldSpec("cancellations_to_date", "integer", minimum=0),
                FieldSpec("group_booking_count", "integer", minimum=0),
                FieldSpec("demand_segment", "string", enum=DEMAND_SEGMENTS),
                FieldSpec("fare_class_mix", "json_string"),
            ),
        ),
        DatasetContract(
            filename="weather_events.csv",
            file_format="csv",
            primary_key=("weather_event_id",),
            foreign_keys={"airport_code": "airports.code"},
            fields=(
                FieldSpec("weather_event_id", "string"),
                FieldSpec("airport_code", "string"),
                FieldSpec("event_start_utc", "timestamp"),
                FieldSpec("event_end_utc", "timestamp"),
                FieldSpec("weather_type", "string", enum=WEATHER_TYPES),
                FieldSpec("severity", "integer", minimum=1, maximum=5),
                FieldSpec("temperature_c", "number"),
                FieldSpec("wind_speed_knots", "number", minimum=0),
                FieldSpec("wind_gust_knots", "number", minimum=0),
                FieldSpec("visibility_metres", "integer", minimum=0),
                FieldSpec("precipitation_mm", "number", minimum=0),
                FieldSpec("operational_impact_score", "number", minimum=0, maximum=100),
            ),
        ),
        DatasetContract(
            filename="aircraft_health.jsonl",
            file_format="jsonl",
            primary_key=("telemetry_id",),
            foreign_keys={"aircraft_id": "fleet.aircraft_id", "flight_id": "flight_schedule.flight_id"},
            fields=(
                FieldSpec("telemetry_id", "string"),
                FieldSpec("aircraft_id", "string"),
                FieldSpec("aircraft_type", "string", enum=SUPPORTED_AIRCRAFT_TYPES),
                FieldSpec("event_timestamp_utc", "timestamp"),
                FieldSpec("flight_id", "string"),
                FieldSpec("engine_1_vibration", "number"),
                FieldSpec("engine_2_vibration", "number"),
                FieldSpec("engine_1_temperature_c", "number"),
                FieldSpec("engine_2_temperature_c", "number"),
                FieldSpec("hydraulic_pressure_psi", "number"),
                FieldSpec("oil_pressure_psi", "number"),
                FieldSpec("fuel_flow_kg_h", "number"),
                FieldSpec("brake_temperature_c", "number"),
                FieldSpec("cycles_since_maintenance", "integer", minimum=0),
                FieldSpec("flight_hours_since_maintenance", "number", minimum=0),
                FieldSpec("fault_code", "string", nullable=True),
                FieldSpec("health_status", "string", enum=HEALTH_STATUSES),
                FieldSpec("maintenance_risk_score", "number", minimum=0, maximum=100),
            ),
        ),
        DatasetContract(
            filename="crew_operations.csv",
            file_format="csv",
            primary_key=("crew_assignment_id",),
            foreign_keys={"flight_id": "flight_schedule.flight_id"},
            fields=(
                FieldSpec("crew_assignment_id", "string"),
                FieldSpec("flight_id", "string"),
                FieldSpec("crew_base", "string"),
                FieldSpec("captain_available", "boolean"),
                FieldSpec("first_officer_available", "boolean"),
                FieldSpec("cabin_crew_required", "integer", minimum=0),
                FieldSpec("cabin_crew_assigned", "integer", minimum=0),
                FieldSpec("reserve_crew_used", "boolean"),
                FieldSpec("duty_start_utc", "timestamp"),
                FieldSpec("duty_end_utc", "timestamp"),
                FieldSpec("duty_minutes", "integer", minimum=0),
                FieldSpec("connection_risk_minutes", "integer", minimum=0),
                FieldSpec("crew_disruption_flag", "boolean"),
                FieldSpec("crew_disruption_reason", "string", nullable=True),
            ),
        ),
        DatasetContract(
            filename="delay_history.csv",
            file_format="csv",
            primary_key=("flight_id",),
            foreign_keys={"flight_id": "flight_schedule.flight_id", "diversion_airport": "airports.code"},
            fields=(
                FieldSpec("flight_id", "string"),
                FieldSpec("actual_departure_utc", "timestamp", nullable=True),
                FieldSpec("actual_arrival_utc", "timestamp", nullable=True),
                FieldSpec("departure_delay_minutes", "integer"),
                FieldSpec("arrival_delay_minutes", "integer", nullable=True),
                FieldSpec("delay_category", "string", enum=DELAY_CATEGORIES),
                FieldSpec("primary_delay_cause", "string", enum=DELAY_CAUSES),
                FieldSpec("secondary_delay_cause", "string", nullable=True),
                FieldSpec("taxi_out_minutes", "integer", nullable=True, minimum=0),
                FieldSpec("taxi_in_minutes", "integer", nullable=True, minimum=0),
                FieldSpec("airborne_minutes", "integer", nullable=True, minimum=0),
                FieldSpec("cancelled_flag", "boolean"),
                FieldSpec("diverted_flag", "boolean"),
                FieldSpec("diversion_airport", "string", nullable=True),
                FieldSpec("reactionary_delay_minutes", "integer", minimum=0),
                FieldSpec("weather_impact_score", "number", minimum=0, maximum=100),
                FieldSpec("airport_impact_score", "number", minimum=0, maximum=100),
                FieldSpec("crew_impact_score", "number", minimum=0, maximum=100),
                FieldSpec("aircraft_impact_score", "number", minimum=0, maximum=100),
            ),
        ),
        DatasetContract(
            filename="airport_events.jsonl",
            file_format="jsonl",
            primary_key=("airport_event_id",),
            foreign_keys={"airport_code": "airports.code"},
            fields=(
                FieldSpec("airport_event_id", "string"),
                FieldSpec("airport_code", "string"),
                FieldSpec("event_start_utc", "timestamp"),
                FieldSpec("event_end_utc", "timestamp"),
                FieldSpec("event_type", "string", enum=AIRPORT_EVENT_TYPES),
                FieldSpec("severity", "integer", minimum=1, maximum=5),
                FieldSpec("capacity_reduction_percent", "integer", minimum=0, maximum=100),
                FieldSpec("affected_terminal", "string"),
                FieldSpec("affected_runway", "string"),
                FieldSpec("estimated_delay_minutes", "integer", minimum=0),
                FieldSpec("event_status", "string", enum=AIRPORT_EVENT_STATUSES),
                FieldSpec("operational_notes", "string"),
            ),
        ),
    ]
    return {contract.filename: contract for contract in contracts}
