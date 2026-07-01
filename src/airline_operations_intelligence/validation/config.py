"""Configuration parsing for governed ingestion and validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import ValidationConfigurationError

DEFAULT_VALIDATION_CONFIG_PATH = Path("configs/validation.yaml")
SUPPORTED_POLICIES = {"reject", "warn", "ignore"}
SUPPORTED_DUPLICATE_POLICIES = {"quarantine", "reject"}
SUPPORTED_SEVERITIES = {"info", "warning", "error", "fatal"}
SUPPORTED_RULE_GROUPS = {"manifest", "schema", "primary_key", "business", "relationships"}


@dataclass(frozen=True)
class ValidationSettings:
    """Validated settings controlling a validation run."""

    profile: str
    fail_on_error: bool
    fail_on_warning: bool
    quarantine_invalid_records: bool
    allow_empty_datasets: bool
    verify_source_checksums: bool
    verify_manifest_row_counts: bool
    strict_schema: bool
    unknown_column_policy: str
    missing_column_policy: str
    duplicate_policy: str
    output_interim_root: Path
    output_processed_root: Path
    report_root: Path
    overwrite: bool
    enabled_rule_groups: tuple[str, ...]
    max_error_count: int
    max_fatal_count: int
    max_warning_count: int
    accepted_timestamp_formats: tuple[str, ...]
    nullable_fields: dict[str, tuple[str, ...]]
    score_min: float
    score_max: float
    probability_min: float
    probability_max: float
    early_departure_allowance_minutes: int
    controlled_overbooking_tolerance: float
    timestamp_overlap_tolerance_minutes: int
    max_invalid_record_rate: float
    warning_invalid_record_rate: float
    booking_velocity_max: float
    temperature_min_c: float
    temperature_max_c: float
    write_empty_quarantine_files: bool
    json_indent: int


@dataclass(frozen=True)
class ValidationConfig:
    """Top-level validation configuration."""

    settings: ValidationSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return a deterministic JSON-serialisable configuration snapshot."""
        settings = self.settings
        return {
            "validation": {
                "profile": settings.profile,
                "fail_on_error": settings.fail_on_error,
                "fail_on_warning": settings.fail_on_warning,
                "quarantine_invalid_records": settings.quarantine_invalid_records,
                "allow_empty_datasets": settings.allow_empty_datasets,
                "verify_source_checksums": settings.verify_source_checksums,
                "verify_manifest_row_counts": settings.verify_manifest_row_counts,
                "strict_schema": settings.strict_schema,
                "unknown_column_policy": settings.unknown_column_policy,
                "missing_column_policy": settings.missing_column_policy,
                "duplicate_policy": settings.duplicate_policy,
                "output_interim_root": settings.output_interim_root.as_posix(),
                "output_processed_root": settings.output_processed_root.as_posix(),
                "report_root": settings.report_root.as_posix(),
                "overwrite": settings.overwrite,
                "enabled_rule_groups": list(settings.enabled_rule_groups),
                "severity_thresholds": {
                    "max_error_count": settings.max_error_count,
                    "max_fatal_count": settings.max_fatal_count,
                    "max_warning_count": settings.max_warning_count,
                },
                "accepted_timestamp_formats": list(settings.accepted_timestamp_formats),
                "nullable_fields": {key: list(value) for key, value in sorted(settings.nullable_fields.items())},
                "ranges": {
                    "score_min": settings.score_min,
                    "score_max": settings.score_max,
                    "probability_min": settings.probability_min,
                    "probability_max": settings.probability_max,
                    "early_departure_allowance_minutes": settings.early_departure_allowance_minutes,
                    "controlled_overbooking_tolerance": settings.controlled_overbooking_tolerance,
                    "timestamp_overlap_tolerance_minutes": settings.timestamp_overlap_tolerance_minutes,
                    "max_invalid_record_rate": settings.max_invalid_record_rate,
                    "warning_invalid_record_rate": settings.warning_invalid_record_rate,
                    "booking_velocity_max": settings.booking_velocity_max,
                    "temperature_min_c": settings.temperature_min_c,
                    "temperature_max_c": settings.temperature_max_c,
                },
                "output": {
                    "write_empty_quarantine_files": settings.write_empty_quarantine_files,
                    "json_indent": settings.json_indent,
                },
            }
        }

    def fingerprint(self) -> str:
        """Return a stable fingerprint of the effective configuration."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_validation_config(path: Path | str) -> ValidationConfig:
    """Load validation configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise ValidationConfigurationError(f"Validation configuration file not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationConfigurationError(f"Validation configuration is not valid YAML: {config_path}") from exc
    if not isinstance(raw, dict):
        raise ValidationConfigurationError("Validation configuration root must be a mapping.")
    return parse_validation_config(raw)


def parse_validation_config(raw: dict[str, Any]) -> ValidationConfig:
    """Validate a raw validation configuration mapping."""
    validation = _mapping(raw, "validation")
    thresholds = _mapping(validation, "severity_thresholds")
    ranges = _mapping(validation, "ranges")
    output = _mapping(validation, "output")
    enabled = tuple(_list_of_strings(validation, "enabled_rule_groups"))
    _reject_duplicates(enabled, "enabled validation rule groups")
    unknown_groups = sorted(set(enabled) - SUPPORTED_RULE_GROUPS)
    if unknown_groups:
        raise ValidationConfigurationError(f"Unknown validation rule groups: {', '.join(unknown_groups)}")
    nullable = {
        str(dataset): tuple(_strings(value, f"nullable_fields.{dataset}"))
        for dataset, value in _mapping(validation, "nullable_fields").items()
    }
    settings = ValidationSettings(
        profile=_str(validation.get("profile", "development"), "validation.profile"),
        fail_on_error=_bool(validation.get("fail_on_error"), "validation.fail_on_error"),
        fail_on_warning=_bool(validation.get("fail_on_warning"), "validation.fail_on_warning"),
        quarantine_invalid_records=_bool(
            validation.get("quarantine_invalid_records"), "validation.quarantine_invalid_records"
        ),
        allow_empty_datasets=_bool(validation.get("allow_empty_datasets"), "validation.allow_empty_datasets"),
        verify_source_checksums=_bool(validation.get("verify_source_checksums"), "validation.verify_source_checksums"),
        verify_manifest_row_counts=_bool(
            validation.get("verify_manifest_row_counts"), "validation.verify_manifest_row_counts"
        ),
        strict_schema=_bool(validation.get("strict_schema"), "validation.strict_schema"),
        unknown_column_policy=_policy(validation.get("unknown_column_policy"), "validation.unknown_column_policy"),
        missing_column_policy=_policy(validation.get("missing_column_policy"), "validation.missing_column_policy"),
        duplicate_policy=_duplicate_policy(validation.get("duplicate_policy")),
        output_interim_root=_root(validation.get("output_interim_root"), ("data", "interim")),
        output_processed_root=_root(validation.get("output_processed_root"), ("data", "processed")),
        report_root=_root(validation.get("report_root"), ("reports", "validation")),
        overwrite=_bool(validation.get("overwrite"), "validation.overwrite"),
        enabled_rule_groups=enabled,
        max_error_count=_non_negative_int(thresholds.get("max_error_count"), "severity_thresholds.max_error_count"),
        max_fatal_count=_non_negative_int(thresholds.get("max_fatal_count"), "severity_thresholds.max_fatal_count"),
        max_warning_count=_non_negative_int(
            thresholds.get("max_warning_count"), "severity_thresholds.max_warning_count"
        ),
        accepted_timestamp_formats=tuple(_list_of_strings(validation, "accepted_timestamp_formats")),
        nullable_fields=nullable,
        score_min=_number(ranges.get("score_min"), "ranges.score_min"),
        score_max=_number(ranges.get("score_max"), "ranges.score_max"),
        probability_min=_probability(ranges.get("probability_min"), "ranges.probability_min"),
        probability_max=_probability(ranges.get("probability_max"), "ranges.probability_max"),
        early_departure_allowance_minutes=_non_negative_int(
            ranges.get("early_departure_allowance_minutes"), "ranges.early_departure_allowance_minutes"
        ),
        controlled_overbooking_tolerance=_ratio(
            ranges.get("controlled_overbooking_tolerance"), "ranges.controlled_overbooking_tolerance"
        ),
        timestamp_overlap_tolerance_minutes=_non_negative_int(
            ranges.get("timestamp_overlap_tolerance_minutes"), "ranges.timestamp_overlap_tolerance_minutes"
        ),
        max_invalid_record_rate=_probability(ranges.get("max_invalid_record_rate"), "ranges.max_invalid_record_rate"),
        warning_invalid_record_rate=_probability(
            ranges.get("warning_invalid_record_rate"), "ranges.warning_invalid_record_rate"
        ),
        booking_velocity_max=_positive_number(ranges.get("booking_velocity_max"), "ranges.booking_velocity_max"),
        temperature_min_c=_number(ranges.get("temperature_min_c"), "ranges.temperature_min_c"),
        temperature_max_c=_number(ranges.get("temperature_max_c"), "ranges.temperature_max_c"),
        write_empty_quarantine_files=_bool(
            output.get("write_empty_quarantine_files"), "output.write_empty_quarantine_files"
        ),
        json_indent=_positive_int(output.get("json_indent"), "output.json_indent"),
    )
    if settings.score_min >= settings.score_max:
        raise ValidationConfigurationError("ranges.score_min must be below ranges.score_max.")
    if settings.probability_min > settings.probability_max:
        raise ValidationConfigurationError("ranges.probability_min must be below or equal to probability_max.")
    if settings.temperature_min_c >= settings.temperature_max_c:
        raise ValidationConfigurationError("ranges.temperature_min_c must be below temperature_max_c.")
    if settings.strict_schema and settings.unknown_column_policy == "ignore":
        raise ValidationConfigurationError("strict_schema cannot be combined with unknown_column_policy=ignore.")
    return ValidationConfig(settings=settings)


def with_overrides(
    config: ValidationConfig,
    *,
    interim_root: Path | None = None,
    processed_root: Path | None = None,
    report_root: Path | None = None,
    overwrite: bool | None = None,
    fail_on_warning: bool | None = None,
    quarantine_invalid_records: bool | None = None,
) -> ValidationConfig:
    """Return a copy of config with CLI overrides applied."""
    current = config.settings
    return ValidationConfig(
        settings=ValidationSettings(
            profile=current.profile,
            fail_on_error=current.fail_on_error,
            fail_on_warning=current.fail_on_warning if fail_on_warning is None else fail_on_warning,
            quarantine_invalid_records=(
                current.quarantine_invalid_records if quarantine_invalid_records is None else quarantine_invalid_records
            ),
            allow_empty_datasets=current.allow_empty_datasets,
            verify_source_checksums=current.verify_source_checksums,
            verify_manifest_row_counts=current.verify_manifest_row_counts,
            strict_schema=current.strict_schema,
            unknown_column_policy=current.unknown_column_policy,
            missing_column_policy=current.missing_column_policy,
            duplicate_policy=current.duplicate_policy,
            output_interim_root=current.output_interim_root
            if interim_root is None
            else _root(interim_root, ("data", "interim")),
            output_processed_root=(
                current.output_processed_root
                if processed_root is None
                else _root(processed_root, ("data", "processed"))
            ),
            report_root=current.report_root if report_root is None else _root(report_root, ("reports", "validation")),
            overwrite=current.overwrite if overwrite is None else overwrite,
            enabled_rule_groups=current.enabled_rule_groups,
            max_error_count=current.max_error_count,
            max_fatal_count=current.max_fatal_count,
            max_warning_count=current.max_warning_count,
            accepted_timestamp_formats=current.accepted_timestamp_formats,
            nullable_fields=current.nullable_fields,
            score_min=current.score_min,
            score_max=current.score_max,
            probability_min=current.probability_min,
            probability_max=current.probability_max,
            early_departure_allowance_minutes=current.early_departure_allowance_minutes,
            controlled_overbooking_tolerance=current.controlled_overbooking_tolerance,
            timestamp_overlap_tolerance_minutes=current.timestamp_overlap_tolerance_minutes,
            max_invalid_record_rate=current.max_invalid_record_rate,
            warning_invalid_record_rate=current.warning_invalid_record_rate,
            booking_velocity_max=current.booking_velocity_max,
            temperature_min_c=current.temperature_min_c,
            temperature_max_c=current.temperature_max_c,
            write_empty_quarantine_files=current.write_empty_quarantine_files,
            json_indent=current.json_indent,
        )
    )


def build_validation_run_id(config: ValidationConfig, source_run_id: str, explicit_run_id: str | None = None) -> str:
    """Build a deterministic filesystem-safe validation run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", explicit_run_id):
            raise ValidationConfigurationError("validation_run_id may contain only letters, numbers, '.', '_', '-'.")
        return explicit_run_id
    profile = re.sub(r"[^A-Za-z0-9._-]+", "-", config.settings.profile).strip("-").lower()
    return f"{profile}-{source_run_id}-{config.fingerprint()[:10]}"


def _mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValidationConfigurationError(f"{key} must be present and must be a mapping.")
    return value


def _str(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationConfigurationError(f"{key} must be a non-empty string.")
    return value


def _strings(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValidationConfigurationError(f"{key} must be a list of non-empty strings.")
    return value


def _list_of_strings(raw: dict[str, Any], key: str) -> list[str]:
    return _strings(raw.get(key), key)


def _bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationConfigurationError(f"{key} must be a boolean.")
    return value


def _non_negative_int(value: Any, key: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValidationConfigurationError(f"{key} must be a non-negative integer.")
    return value


def _positive_int(value: Any, key: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValidationConfigurationError(f"{key} must be a positive integer.")
    return value


def _number(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise ValidationConfigurationError(f"{key} must be numeric.")
    return float(value)


def _positive_number(value: Any, key: str) -> float:
    number = _number(value, key)
    if number <= 0:
        raise ValidationConfigurationError(f"{key} must be positive.")
    return number


def _probability(value: Any, key: str) -> float:
    number = _number(value, key)
    if number < 0 or number > 1:
        raise ValidationConfigurationError(f"{key} must be between 0 and 1.")
    return number


def _ratio(value: Any, key: str) -> float:
    number = _number(value, key)
    if number < 1:
        raise ValidationConfigurationError(f"{key} must be at least 1.")
    return number


def _policy(value: Any, key: str) -> str:
    policy = _str(value, key)
    if policy not in SUPPORTED_POLICIES:
        raise ValidationConfigurationError(f"{key} must be one of {sorted(SUPPORTED_POLICIES)}.")
    return policy


def _duplicate_policy(value: Any) -> str:
    policy = _str(value, "validation.duplicate_policy")
    if policy not in SUPPORTED_DUPLICATE_POLICIES:
        raise ValidationConfigurationError(
            f"validation.duplicate_policy must be one of {sorted(SUPPORTED_DUPLICATE_POLICIES)}."
        )
    return policy


def _root(value: Any, expected_prefix: tuple[str, ...]) -> Path:
    root = Path(_str(str(value), ".".join(expected_prefix)))
    if root.is_absolute() or ".." in root.parts:
        raise ValidationConfigurationError(f"{root} must be repository-relative and cannot contain '..'.")
    if len(root.parts) < len(expected_prefix) or root.parts[: len(expected_prefix)] != expected_prefix:
        raise ValidationConfigurationError(f"{root} must be under {'/'.join(expected_prefix)}.")
    return Path(*root.parts)


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValidationConfigurationError(f"Duplicate {label}: {value}")
        seen.add(value)
