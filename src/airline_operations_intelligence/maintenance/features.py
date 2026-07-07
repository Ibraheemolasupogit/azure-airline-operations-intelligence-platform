"""Feature construction for aircraft-health analytics."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from airline_operations_intelligence.common.exceptions import MaintenanceFeatureEngineeringError
from airline_operations_intelligence.maintenance.config import MaintenanceAnalyticsConfig, TelemetryBound
from airline_operations_intelligence.maintenance.contracts import HealthFeatureRow, MaintenanceSource
from airline_operations_intelligence.maintenance.dataset import read_csv, read_jsonl


def build_health_features(source: MaintenanceSource, config: MaintenanceAnalyticsConfig) -> list[HealthFeatureRow]:
    """Build deterministic aircraft-health feature rows."""
    telemetry = read_jsonl(source.processed_dir / "aircraft_health.jsonl")
    schedule = {row["flight_id"]: row for row in read_csv(source.processed_dir / "flight_schedule.csv")}
    delays = {row["flight_id"]: row for row in read_csv(source.processed_dir / "delay_history.csv")}
    history: dict[str, list[HealthFeatureRow]] = defaultdict(list)
    rows: list[HealthFeatureRow] = []
    for raw in sorted(telemetry, key=lambda row: (str(row["event_timestamp_utc"]), str(row["telemetry_id"]))):
        aircraft_id = str(raw["aircraft_id"])
        flight_id = str(raw.get("flight_id") or "")
        event_ts = _parse_dt(str(raw["event_timestamp_utc"]))
        flight = schedule.get(flight_id, {})
        delay = delays.get(flight_id, {})
        prior = history[aircraft_id]
        features = _base_features(raw, config.settings.telemetry_bounds)
        features.update(_rolling_features(prior, config))
        features.update(_operational_context(prior, flight, delay))
        context: dict[str, float | str | bool] = {
            "linked_route_id": str(flight.get("route_id", "")),
            "linked_scheduled_block_minutes": _float(flight.get("scheduled_block_minutes", 0.0)),
            "retrospective_departure_delay_minutes": _float(delay.get("departure_delay_minutes", 0.0)),
            "retrospective_context_only": True,
        }
        row = HealthFeatureRow(
            health_observation_id=f"{aircraft_id}:{raw['telemetry_id']}",
            aircraft_id=aircraft_id,
            aircraft_type=str(raw["aircraft_type"]),
            telemetry_id=str(raw["telemetry_id"]),
            flight_id=flight_id,
            event_timestamp_utc=event_ts,
            operating_date=str(flight.get("operating_date", event_ts.date().isoformat())),
            features=features,
            context=context,
        )
        history[aircraft_id].append(row)
        rows.append(row)
    if not rows:
        raise MaintenanceFeatureEngineeringError("No aircraft telemetry rows were available for maintenance analytics.")
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.aircraft_id] += 1
    filtered = [row for row in rows if counts[row.aircraft_id] >= config.settings.minimum_aircraft_observations]
    if not filtered:
        raise MaintenanceFeatureEngineeringError("No aircraft met minimum_aircraft_observations.")
    return filtered


def _base_features(raw: dict[str, object], bounds: dict[str, TelemetryBound]) -> dict[str, float | str | bool]:
    e1_vib = _float(raw["engine_1_vibration"])
    e2_vib = _float(raw["engine_2_vibration"])
    e1_temp = _float(raw["engine_1_temperature_c"])
    e2_temp = _float(raw["engine_2_temperature_c"])
    features: dict[str, float | str | bool] = {
        "engine_1_vibration": e1_vib,
        "engine_2_vibration": e2_vib,
        "engine_vibration_max": max(e1_vib, e2_vib),
        "engine_vibration_delta": abs(e1_vib - e2_vib),
        "engine_1_temperature_c": e1_temp,
        "engine_2_temperature_c": e2_temp,
        "engine_temperature_max": max(e1_temp, e2_temp),
        "engine_temperature_delta": abs(e1_temp - e2_temp),
        "hydraulic_pressure_psi": _float(raw["hydraulic_pressure_psi"]),
        "oil_pressure_psi": _float(raw["oil_pressure_psi"]),
        "fuel_flow_kg_h": _float(raw["fuel_flow_kg_h"]),
        "brake_temperature_c": _float(raw["brake_temperature_c"]),
        "cycles_since_maintenance": _float(raw["cycles_since_maintenance"]),
        "flight_hours_since_maintenance": _float(raw["flight_hours_since_maintenance"]),
        "source_maintenance_risk_score": _float(raw["maintenance_risk_score"]) / 100.0,
        "health_status": str(raw["health_status"]),
        "fault_code": "" if raw.get("fault_code") is None else str(raw["fault_code"]),
    }
    features["fault_code_present"] = bool(features["fault_code"])
    features.update(_sensor_flags(features, bounds))
    return features


def _sensor_flags(features: dict[str, float | str | bool], bounds: dict[str, TelemetryBound]) -> dict[str, bool]:
    return {
        "vibration_warning_flag": _breaches(
            _num(features["engine_vibration_max"]), bounds["engine_1_vibration"], False
        ),
        "vibration_critical_flag": _breaches(
            _num(features["engine_vibration_max"]), bounds["engine_1_vibration"], True
        ),
        "engine_temperature_warning_flag": _breaches(
            _num(features["engine_temperature_max"]), bounds["engine_1_temperature_c"], False
        ),
        "engine_temperature_critical_flag": _breaches(
            _num(features["engine_temperature_max"]), bounds["engine_1_temperature_c"], True
        ),
        "hydraulic_pressure_warning_flag": _breaches(
            _num(features["hydraulic_pressure_psi"]), bounds["hydraulic_pressure_psi"], False
        ),
        "hydraulic_pressure_critical_flag": _breaches(
            _num(features["hydraulic_pressure_psi"]), bounds["hydraulic_pressure_psi"], True
        ),
        "oil_pressure_warning_flag": _breaches(_num(features["oil_pressure_psi"]), bounds["oil_pressure_psi"], False),
        "oil_pressure_critical_flag": _breaches(_num(features["oil_pressure_psi"]), bounds["oil_pressure_psi"], True),
        "brake_temperature_warning_flag": _breaches(
            _num(features["brake_temperature_c"]), bounds["brake_temperature_c"], False
        ),
        "brake_temperature_critical_flag": _breaches(
            _num(features["brake_temperature_c"]), bounds["brake_temperature_c"], True
        ),
    }


def _rolling_features(prior: list[HealthFeatureRow], config: MaintenanceAnalyticsConfig) -> dict[str, float]:
    window = config.settings.rolling_windows[0]
    recent = prior[-window:]
    if not recent:
        return {
            "rolling_average_vibration": 0.0,
            "rolling_max_temperature": 0.0,
            "rolling_brake_temperature": 0.0,
            "rolling_fault_code_count": 0.0,
            "recent_cycles_since_maintenance": 0.0,
            "recent_flight_hours_since_maintenance": 0.0,
            "utilisation_intensity": 0.0,
            "degradation_trend_score": 0.0,
        }
    avg_vibration = sum(_num(row.features["engine_vibration_max"]) for row in recent) / len(recent)
    max_temp = max(_num(row.features["engine_temperature_max"]) for row in recent)
    avg_brake = sum(_num(row.features["brake_temperature_c"]) for row in recent) / len(recent)
    fault_count = sum(1 for row in recent if bool(row.features["fault_code_present"]))
    cycles = _num(recent[-1].features["cycles_since_maintenance"])
    hours = _num(recent[-1].features["flight_hours_since_maintenance"])
    source_risk_delta = _num(recent[-1].features["source_maintenance_risk_score"]) - _num(
        recent[0].features["source_maintenance_risk_score"]
    )
    trend = _bounded(max(0.0, source_risk_delta) + max(0.0, avg_vibration - 3.0) / 6.0 + fault_count / max(1, window))
    return {
        "rolling_average_vibration": avg_vibration,
        "rolling_max_temperature": max_temp,
        "rolling_brake_temperature": avg_brake,
        "rolling_fault_code_count": float(fault_count),
        "recent_cycles_since_maintenance": cycles,
        "recent_flight_hours_since_maintenance": hours,
        "utilisation_intensity": _bounded((cycles / 450.0 + hours / 1200.0) / 2),
        "degradation_trend_score": trend,
    }


def _operational_context(
    prior: list[HealthFeatureRow], flight: dict[str, str], delay: dict[str, str]
) -> dict[str, float | str | bool]:
    aircraft_delay_rate = 0.0
    if prior:
        delayed = sum(1 for row in prior if _num(row.context.get("retrospective_departure_delay_minutes", 0.0)) >= 15)
        aircraft_delay_rate = delayed / len(prior)
    return {
        "linked_flight_route": str(flight.get("route_id", "")),
        "linked_scheduled_block_minutes": _float(flight.get("scheduled_block_minutes", 0.0)),
        "linked_departure_delay_minutes_retrospective": _float(delay.get("departure_delay_minutes", 0.0)),
        "recent_aircraft_delay_rate": aircraft_delay_rate,
    }


def _breaches(value: float, bound: TelemetryBound, critical: bool) -> bool:
    lower = bound.critical_min if critical else bound.warning_min
    upper = bound.critical_max if critical else bound.warning_max
    return (lower is not None and value < lower) or (upper is not None and value > upper)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _float(value: object) -> float:
    if value in {"", None}:
        return 0.0
    if isinstance(value, int | float | str):
        return float(value)
    return 0.0


def _num(value: object) -> float:
    return _float(value)


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
