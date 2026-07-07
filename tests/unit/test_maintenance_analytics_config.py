from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import MaintenanceAnalyticsConfigurationError
from airline_operations_intelligence.maintenance.config import (
    build_maintenance_run_id,
    load_maintenance_config,
    parse_maintenance_config,
    with_overrides,
)


def test_maintenance_config_loads_ci_profile() -> None:
    config = load_maintenance_config("configs/maintenance_analytics_ci.yaml")

    assert config.settings.seed == 7
    assert config.settings.risk_weights["sensor_thresholds"] == 0.30
    assert config.settings.maximum_alerts_per_aircraft == 4


def test_maintenance_config_rejects_bad_output_root() -> None:
    raw = _minimal_raw_config()
    raw["maintenance_analytics"]["output_root"] = "data/raw/maintenance"

    with pytest.raises(MaintenanceAnalyticsConfigurationError, match="outputs/maintenance_analytics"):
        parse_maintenance_config(raw)


def test_maintenance_config_rejects_non_monotonic_thresholds() -> None:
    raw = _minimal_raw_config()
    raw["maintenance_analytics"]["alert_thresholds"]["watch"] = 0.1

    with pytest.raises(MaintenanceAnalyticsConfigurationError, match="monotonic"):
        parse_maintenance_config(raw)


def test_maintenance_config_rejects_bad_weight_sum() -> None:
    raw = _minimal_raw_config()
    raw["risk_weights"]["utilisation"] = 0.2

    with pytest.raises(MaintenanceAnalyticsConfigurationError, match="sum to 1.0"):
        parse_maintenance_config(raw)


def test_maintenance_run_id_and_overrides_are_deterministic() -> None:
    config = load_maintenance_config("configs/maintenance_analytics_ci.yaml")
    updated = with_overrides(config, output_root=Path("outputs/maintenance_analytics/test"), seed=99, overwrite=True)

    assert updated.settings.seed == 99
    assert updated.settings.overwrite is True
    assert build_maintenance_run_id(config, "validation-a", "0.1.0") == build_maintenance_run_id(
        config, "validation-a", "0.1.0"
    )
    assert build_maintenance_run_id(config, "validation-a", "0.1.0", "manual") == "manual"


def _minimal_raw_config() -> dict[str, object]:
    return {
        "maintenance_analytics": {
            "output_root": "outputs/maintenance_analytics",
            "report_root": "reports/maintenance_analytics",
            "overwrite": False,
            "seed": 1,
            "accepted_validation_status": ["passed"],
            "risk_score_thresholds": {"low": 0.1, "medium": 0.2, "high": 0.3},
            "alert_thresholds": {"advisory": 0.1, "watch": 0.2, "action_recommended": 0.3},
            "rolling_windows": [3],
            "enable_statistical_anomaly_detection": True,
            "enable_flight_level_risk": True,
            "minimum_aircraft_observations": 1,
            "maximum_alerts_per_aircraft": 2,
        },
        "telemetry_bounds": {
            "engine_1_vibration": {"warning_min": 0.0, "warning_max": 6.0, "critical_max": 8.0},
            "engine_2_vibration": {"warning_min": 0.0, "warning_max": 6.0, "critical_max": 8.0},
            "engine_1_temperature_c": {"warning_min": 200.0, "warning_max": 850.0, "critical_max": 950.0},
            "engine_2_temperature_c": {"warning_min": 200.0, "warning_max": 850.0, "critical_max": 950.0},
            "hydraulic_pressure_psi": {
                "warning_min": 2500.0,
                "warning_max": 3500.0,
                "critical_min": 2000.0,
                "critical_max": 4000.0,
            },
            "oil_pressure_psi": {
                "warning_min": 35.0,
                "warning_max": 90.0,
                "critical_min": 20.0,
                "critical_max": 110.0,
            },
            "brake_temperature_c": {"warning_min": 0.0, "warning_max": 350.0, "critical_max": 500.0},
        },
        "risk_weights": {
            "sensor_thresholds": 0.30,
            "telemetry_anomaly": 0.20,
            "degradation_trend": 0.20,
            "fault_code": 0.15,
            "utilisation": 0.10,
            "recent_delay_or_operational_context": 0.05,
        },
    }
