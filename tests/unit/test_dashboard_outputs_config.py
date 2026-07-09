from __future__ import annotations

from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import DashboardConfigurationError
from airline_operations_intelligence.dashboard.config import (
    build_dashboard_run_id,
    load_dashboard_config,
    parse_dashboard_config,
    with_overrides,
)


def test_dashboard_config_parses_ci_defaults() -> None:
    config = load_dashboard_config(_repo_root() / "configs/dashboard_outputs_ci.yaml")

    assert config.settings.output_root == Path("dashboard/outputs")
    assert config.settings.report_root == Path("reports/dashboard_outputs")
    assert config.settings.export_format == ("csv", "json")
    assert config.semantic_model.model_name == "Airline Operations Intelligence CI"
    assert config.kpi_thresholds["high_delay_rate"] == 0.25


def test_dashboard_config_rejects_invalid_values() -> None:
    raw = _valid_raw()
    raw["dashboard_outputs"]["export_format"] = ["csv", "csv"]
    with pytest.raises(DashboardConfigurationError, match="Duplicate"):
        parse_dashboard_config(raw)

    raw = _valid_raw()
    raw["dashboard_outputs"]["output_root"] = "/tmp/dashboard"
    with pytest.raises(DashboardConfigurationError, match="must remain under"):
        parse_dashboard_config(raw)

    raw = _valid_raw()
    raw["kpi_thresholds"]["high_delay_rate"] = 1.5
    with pytest.raises(DashboardConfigurationError, match=r"\[0, 1\]"):
        parse_dashboard_config(raw)

    raw = _valid_raw()
    raw["semantic_model"]["timezone"] = "Mars/Base"
    with pytest.raises(DashboardConfigurationError, match="timezone"):
        parse_dashboard_config(raw)


def test_dashboard_overrides_and_run_id_are_deterministic() -> None:
    config = load_dashboard_config(_repo_root() / "configs/dashboard_outputs_ci.yaml")
    overridden = with_overrides(config, seed=99, overwrite=False, output_root=Path("dashboard/outputs"))
    first = build_dashboard_run_id(overridden, "val", "disr", "mon", ("fcst",), "1.0")
    second = build_dashboard_run_id(overridden, "val", "disr", "mon", ("fcst",), "1.0")

    assert overridden.settings.seed == 99
    assert not overridden.settings.overwrite
    assert first == second
    assert first.startswith("dashboard-val-")
    with pytest.raises(DashboardConfigurationError, match="dashboard_run_id"):
        build_dashboard_run_id(config, "val", "disr", "mon", (), "1.0", "bad/run")


def _valid_raw() -> dict:
    return {
        "dashboard_outputs": {
            "output_root": "dashboard/outputs",
            "report_root": "reports/dashboard_outputs",
            "overwrite": False,
            "seed": 42,
            "export_format": ["csv", "json"],
            "include_powerbi_model_spec": True,
            "include_measure_catalogue": True,
            "include_page_specs": True,
            "include_data_dictionary": True,
            "maximum_example_records": 20,
        },
        "input_options": {
            "require_disruption_input": True,
            "require_monitoring_input": True,
            "use_passenger_forecast": True,
            "use_delay_prediction": True,
            "use_maintenance_analytics": True,
            "use_genai_assistant": True,
        },
        "semantic_model": {
            "model_name": "Airline Operations Intelligence",
            "date_table_start": "2025-01-01",
            "date_table_end": "2025-12-31",
            "currency_code": "GBP",
            "timezone": "UTC",
            "surrogate_key_prefix": "SK",
            "unknown_member_label": "Unknown",
        },
        "kpi_thresholds": {
            "high_delay_rate": 0.25,
            "severe_disruption_rate": 0.20,
            "high_maintenance_risk_rate": 0.20,
            "validation_invalid_rate_warning": 0.01,
            "monitoring_alert_rate_warning": 0.10,
        },
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
