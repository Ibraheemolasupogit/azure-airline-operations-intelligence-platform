from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import DisruptionScoringConfigurationError
from airline_operations_intelligence.disruption.config import (
    build_disruption_run_id,
    load_disruption_config,
    parse_disruption_config,
    with_overrides,
)


def test_disruption_config_loads_ci_profile() -> None:
    config = load_disruption_config("configs/disruption_scoring_ci.yaml")

    assert config.settings.seed == 7
    assert config.settings.maximum_alerts_per_run == 12
    assert config.settings.component_weights["delay"] == 0.25


def test_disruption_config_rejects_bad_output_root() -> None:
    raw = _minimal_raw_config()
    raw["disruption_scoring"]["output_root"] = "data/raw/disruption"

    with pytest.raises(DisruptionScoringConfigurationError, match="outputs/disruption_scoring"):
        parse_disruption_config(raw)


def test_disruption_config_rejects_bad_bands() -> None:
    raw = _minimal_raw_config()
    raw["risk_bands"]["medium"]["minimum_score"] = 0.4

    with pytest.raises(DisruptionScoringConfigurationError, match="contiguous"):
        parse_disruption_config(raw)


def test_disruption_config_rejects_bad_weights() -> None:
    raw = _minimal_raw_config()
    raw["component_weights"]["delay"] = 0.5

    with pytest.raises(DisruptionScoringConfigurationError, match="sum to 1.0"):
        parse_disruption_config(raw)


def test_disruption_run_id_and_overrides_are_deterministic() -> None:
    config = load_disruption_config("configs/disruption_scoring_ci.yaml")
    updated = with_overrides(config, output_root=Path("outputs/disruption_scoring/test"), seed=99, overwrite=True)

    assert updated.settings.seed == 99
    assert updated.settings.overwrite is True
    assert build_disruption_run_id(config, "validation-a", (None, None, None), "0.1.0") == build_disruption_run_id(
        config, "validation-a", (None, None, None), "0.1.0"
    )
    assert build_disruption_run_id(config, "validation-a", (None, None, None), "0.1.0", "manual") == "manual"


def _minimal_raw_config() -> dict[str, object]:
    return {
        "disruption_scoring": {
            "output_root": "outputs/disruption_scoring",
            "report_root": "reports/disruption_scoring",
            "overwrite": False,
            "seed": 1,
            "accepted_validation_status": ["passed"],
            "enable_forward_risk_score": True,
            "enable_retrospective_score": True,
            "maximum_alerts_per_run": 10,
        },
        "input_options": {
            "use_passenger_forecast": True,
            "use_delay_prediction": True,
            "use_maintenance_analytics": True,
            "require_optional_inputs": False,
        },
        "risk_bands": {
            "low": {"minimum_score": 0.0, "maximum_score": 0.3},
            "medium": {"minimum_score": 0.3, "maximum_score": 0.6},
            "high": {"minimum_score": 0.6, "maximum_score": 0.8},
            "severe": {"minimum_score": 0.8, "maximum_score": 1.0},
        },
        "recovery_priority": {
            "monitor": {"minimum_score": 0.0, "maximum_score": 0.3},
            "review": {"minimum_score": 0.3, "maximum_score": 0.6},
            "prioritise": {"minimum_score": 0.6, "maximum_score": 0.8},
            "urgent_review": {"minimum_score": 0.8, "maximum_score": 1.0},
        },
        "component_weights": {
            "delay": 0.25,
            "weather": 0.15,
            "airport_events": 0.15,
            "crew": 0.15,
            "aircraft_health": 0.10,
            "passenger_pressure": 0.10,
            "network_reactionary": 0.10,
        },
        "thresholds": {
            "material_delay_minutes": 15,
            "severe_delay_minutes": 60,
            "high_load_factor": 0.90,
            "severe_weather_impact": 0.75,
            "high_airport_capacity_reduction": 40.0,
            "high_crew_connection_risk_minutes": 45,
            "high_maintenance_risk": 0.60,
            "high_reactionary_delay_minutes": 30,
        },
    }
