from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import GenerationConfigurationError
from airline_operations_intelligence.data_generation.config import (
    build_run_id,
    load_generation_config,
    parse_generation_config,
    with_overrides,
)


def test_generation_config_loads_ci_profile() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")

    assert config.settings.profile == "ci"
    assert config.settings.seed == 7
    assert config.settings.number_of_days == 3
    assert config.settings.flights_per_day == 8
    assert "LHR" in config.airport_codes


def test_generation_config_rejects_negative_flights() -> None:
    raw = _minimal_raw_config()
    raw["generation"]["flights_per_day"] = -1

    with pytest.raises(GenerationConfigurationError, match="flights_per_day"):
        parse_generation_config(raw)


def test_generation_config_rejects_unknown_route_airport() -> None:
    raw = _minimal_raw_config()
    raw["reference"]["routes"][0]["destination"] = "ZZZ"

    with pytest.raises(GenerationConfigurationError, match="unknown airport"):
        parse_generation_config(raw)


def test_generation_config_rejects_duplicate_aircraft() -> None:
    raw = _minimal_raw_config()
    raw["reference"]["fleet"].append(dict(raw["reference"]["fleet"][0]))

    with pytest.raises(GenerationConfigurationError, match="Duplicate aircraft"):
        parse_generation_config(raw)


def test_generation_config_rejects_output_outside_data_raw() -> None:
    raw = _minimal_raw_config()
    raw["generation"]["output_root"] = "outputs/raw"

    with pytest.raises(GenerationConfigurationError, match="data/raw"):
        parse_generation_config(raw)


def test_run_id_is_deterministic_and_overridable() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")

    assert build_run_id(config) == build_run_id(config)
    assert build_run_id(config, "manual-run") == "manual-run"


def test_cli_overrides_are_explicit() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")
    updated = with_overrides(config, seed=123, output_root=Path("data/raw/test"), overwrite=True)

    assert updated.settings.seed == 123
    assert updated.settings.output_root == Path("data/raw/test")
    assert updated.settings.overwrite is True


def _minimal_raw_config() -> dict[str, object]:
    return {
        "generation": {
            "profile": "test",
            "seed": 1,
            "start_date": "2025-01-01",
            "number_of_days": 1,
            "flights_per_day": 2,
            "output_root": "data/raw",
            "overwrite": False,
            "anomaly_rate": 0.01,
            "demand_observation_days": [7, 1],
            "max_overbooking_ratio": 1.05,
        },
        "reference": {
            "airports": [{"code": "LHR"}, {"code": "AMS"}],
            "routes": [
                {
                    "route_id": "LHR-AMS",
                    "origin": "LHR",
                    "destination": "AMS",
                    "scheduled_block_minutes": 80,
                    "popularity": 1.0,
                }
            ],
            "aircraft_types": {"A320": {"seat_capacity": 180}},
            "fleet": [{"aircraft_id": "SYN-A320-001", "aircraft_type": "A320", "base_airport": "LHR"}],
            "carriers": ["AO"],
            "crew_bases": ["LHR"],
            "weather_event_probabilities": {"rain": 0.1},
            "airport_event_probabilities": {"terminal_congestion": 0.1},
            "demand_seasonality": {"01": 1.0},
            "delay_cause_probabilities": {"weather": 1.0},
            "sensor_ranges": {
                "A320": {
                    "engine_1_vibration": [0.2, 4.8],
                    "engine_2_vibration": [0.2, 4.8],
                    "engine_1_temperature_c": [540, 760],
                    "engine_2_temperature_c": [540, 760],
                    "hydraulic_pressure_psi": [2850, 3200],
                    "oil_pressure_psi": [42, 75],
                    "fuel_flow_kg_h": [1700, 2900],
                    "brake_temperature_c": [80, 380],
                }
            },
            "maintenance_risk": {"vibration_weight": 1.0},
        },
    }
