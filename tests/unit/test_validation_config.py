from pathlib import Path

import pytest

from airline_operations_intelligence.common.exceptions import ValidationConfigurationError
from airline_operations_intelligence.validation.config import (
    build_validation_run_id,
    load_validation_config,
    parse_validation_config,
    with_overrides,
)


def test_validation_config_loads_ci_profile() -> None:
    config = load_validation_config("configs/validation_ci.yaml")

    assert config.settings.profile == "ci"
    assert config.settings.verify_source_checksums is True
    assert config.settings.output_processed_root == Path("data/processed")


def test_validation_config_rejects_invalid_threshold() -> None:
    raw = _minimal_raw_config()
    raw["validation"]["severity_thresholds"]["max_error_count"] = -1

    with pytest.raises(ValidationConfigurationError, match="max_error_count"):
        parse_validation_config(raw)


def test_validation_config_rejects_output_outside_allowed_root() -> None:
    raw = _minimal_raw_config()
    raw["validation"]["output_processed_root"] = "outputs/processed"

    with pytest.raises(ValidationConfigurationError, match="data/processed"):
        parse_validation_config(raw)


def test_validation_run_id_is_deterministic_and_overridable() -> None:
    config = load_validation_config("configs/validation_ci.yaml")

    assert build_validation_run_id(config, "source-a") == build_validation_run_id(config, "source-a")
    assert build_validation_run_id(config, "source-a", "manual") == "manual"


def test_validation_overrides_are_explicit() -> None:
    config = load_validation_config("configs/validation_ci.yaml")
    updated = with_overrides(
        config,
        processed_root=Path("data/processed/test"),
        overwrite=True,
        fail_on_warning=True,
        quarantine_invalid_records=False,
    )

    assert updated.settings.output_processed_root == Path("data/processed/test")
    assert updated.settings.overwrite is True
    assert updated.settings.fail_on_warning is True
    assert updated.settings.quarantine_invalid_records is False


def _minimal_raw_config() -> dict[str, object]:
    return {
        "validation": {
            "profile": "test",
            "fail_on_error": True,
            "fail_on_warning": False,
            "quarantine_invalid_records": True,
            "allow_empty_datasets": False,
            "verify_source_checksums": True,
            "verify_manifest_row_counts": True,
            "strict_schema": True,
            "unknown_column_policy": "reject",
            "missing_column_policy": "reject",
            "duplicate_policy": "quarantine",
            "output_interim_root": "data/interim",
            "output_processed_root": "data/processed",
            "report_root": "reports/validation",
            "overwrite": False,
            "enabled_rule_groups": ["manifest", "schema", "primary_key", "business", "relationships"],
            "severity_thresholds": {"max_error_count": 0, "max_fatal_count": 0, "max_warning_count": 10},
            "accepted_timestamp_formats": ["iso8601_utc"],
            "nullable_fields": {"delay_history.csv": ["diversion_airport"]},
            "ranges": {
                "score_min": 0,
                "score_max": 100,
                "probability_min": 0,
                "probability_max": 1,
                "early_departure_allowance_minutes": 15,
                "controlled_overbooking_tolerance": 1.08,
                "timestamp_overlap_tolerance_minutes": 30,
                "max_invalid_record_rate": 0.05,
                "warning_invalid_record_rate": 0.01,
                "booking_velocity_max": 20,
                "temperature_min_c": -60,
                "temperature_max_c": 55,
            },
            "output": {"write_empty_quarantine_files": True, "json_indent": 2},
        }
    }
