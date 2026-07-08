from __future__ import annotations

import copy

import pytest

from airline_operations_intelligence.common.exceptions import MonitoringConfigurationError
from airline_operations_intelligence.monitoring.config import parse_monitoring_config


def test_monitoring_config_parses_valid_configuration() -> None:
    config = parse_monitoring_config(_raw_config())

    assert config.settings.output_root.as_posix() == "outputs/monitoring"
    assert config.settings.report_root.as_posix() == "reports/monitoring"
    assert config.settings.accepted_statuses == ("passed", "passed_with_warnings", "completed", "succeeded")
    assert config.settings.severity_policy["critical"] > config.settings.severity_policy["high"]
    assert len(config.fingerprint()) == 64


def test_monitoring_config_rejects_invalid_status() -> None:
    raw = _raw_config()
    raw["monitoring"]["accepted_statuses"] = ["passed", "unknown"]

    with pytest.raises(MonitoringConfigurationError, match="Unsupported"):
        parse_monitoring_config(raw)


def test_monitoring_config_rejects_bad_severity_policy() -> None:
    raw = _raw_config()
    raw["severity_policy"]["critical"] = 1

    with pytest.raises(MonitoringConfigurationError, match="strictly increasing"):
        parse_monitoring_config(raw)


def test_monitoring_config_rejects_unsafe_output_path() -> None:
    raw = _raw_config()
    raw["monitoring"]["output_root"] = "/tmp/monitoring"

    with pytest.raises(MonitoringConfigurationError, match="must remain under"):
        parse_monitoring_config(raw)


def test_monitoring_config_rejects_non_monotonic_thresholds() -> None:
    raw = _raw_config()
    raw["thresholds"]["invalid_record_rate_warning"] = 0.10
    raw["thresholds"]["invalid_record_rate_critical"] = 0.05

    with pytest.raises(MonitoringConfigurationError, match="greater than or equal"):
        parse_monitoring_config(raw)


def _raw_config() -> dict:
    return copy.deepcopy(
        {
            "monitoring": {
                "output_root": "outputs/monitoring",
                "report_root": "reports/monitoring",
                "overwrite": False,
                "seed": 42,
                "accepted_statuses": ["passed", "passed_with_warnings", "completed", "succeeded"],
                "maximum_alerts_per_run": 10,
                "enable_drift_checks": True,
                "enable_model_metric_checks": True,
                "enable_data_quality_checks": True,
                "enable_lineage_checks": True,
                "enable_runtime_checks": True,
            },
            "thresholds": {
                "validation_error_count_warning": 1,
                "validation_error_count_critical": 10,
                "validation_warning_count_warning": 5,
                "invalid_record_rate_warning": 0.01,
                "invalid_record_rate_critical": 0.05,
                "checksum_failure_severity": "critical",
                "missing_lineage_severity": "high",
                "minimum_processed_row_count": 1,
                "max_runtime_seconds_warning": 300,
                "max_runtime_seconds_critical": 900,
                "passenger_forecast_wape_warning": 0.25,
                "passenger_forecast_wape_critical": 0.40,
                "delay_prediction_pr_auc_warning": 0.50,
                "delay_prediction_pr_auc_critical": 0.35,
                "maintenance_high_risk_rate_warning": 0.20,
                "disruption_severe_rate_warning": 0.25,
                "drift_relative_change_warning": 0.25,
                "drift_relative_change_critical": 0.50,
            },
            "severity_policy": {"info": 0, "warning": 1, "high": 2, "critical": 3},
            "monitoring_domains": {
                "generation": True,
                "validation": True,
                "passenger_forecasting": True,
                "delay_prediction": True,
                "maintenance_analytics": True,
                "disruption_scoring": True,
            },
        }
    )
