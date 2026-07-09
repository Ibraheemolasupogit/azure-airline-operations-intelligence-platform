"""Configuration parsing for local dashboard outputs."""

from __future__ import annotations

import hashlib
import json
import re
import zoneinfo
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import DashboardConfigurationError

DEFAULT_DASHBOARD_CONFIG_PATH = Path("configs/dashboard_outputs.yaml")
SUPPORTED_EXPORT_FORMATS = {"csv", "json"}
OPTIONAL_FLAGS = {
    "use_passenger_forecast",
    "use_delay_prediction",
    "use_maintenance_analytics",
    "use_genai_assistant",
}


@dataclass(frozen=True)
class DashboardSettings:
    """Validated dashboard-output settings."""

    output_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    export_format: tuple[str, ...]
    include_powerbi_model_spec: bool
    include_measure_catalogue: bool
    include_page_specs: bool
    include_data_dictionary: bool
    maximum_example_records: int


@dataclass(frozen=True)
class InputOptions:
    """Validated source input requirements."""

    require_disruption_input: bool
    require_monitoring_input: bool
    use_passenger_forecast: bool
    use_delay_prediction: bool
    use_maintenance_analytics: bool
    use_genai_assistant: bool


@dataclass(frozen=True)
class SemanticModelSettings:
    """Validated semantic model metadata."""

    model_name: str
    date_table_start: date
    date_table_end: date
    currency_code: str
    timezone: str
    surrogate_key_prefix: str
    unknown_member_label: str


@dataclass(frozen=True)
class DashboardConfig:
    """Top-level dashboard-output configuration."""

    settings: DashboardSettings
    input_options: InputOptions
    semantic_model: SemanticModelSettings
    kpi_thresholds: dict[str, float]

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        settings = self.settings
        semantic = self.semantic_model
        return {
            "dashboard_outputs": {
                "output_root": settings.output_root.as_posix(),
                "report_root": settings.report_root.as_posix(),
                "overwrite": settings.overwrite,
                "seed": settings.seed,
                "export_format": list(settings.export_format),
                "include_powerbi_model_spec": settings.include_powerbi_model_spec,
                "include_measure_catalogue": settings.include_measure_catalogue,
                "include_page_specs": settings.include_page_specs,
                "include_data_dictionary": settings.include_data_dictionary,
                "maximum_example_records": settings.maximum_example_records,
            },
            "input_options": self.input_options.__dict__,
            "semantic_model": {
                "model_name": semantic.model_name,
                "date_table_start": semantic.date_table_start.isoformat(),
                "date_table_end": semantic.date_table_end.isoformat(),
                "currency_code": semantic.currency_code,
                "timezone": semantic.timezone,
                "surrogate_key_prefix": semantic.surrogate_key_prefix,
                "unknown_member_label": semantic.unknown_member_label,
            },
            "kpi_thresholds": dict(sorted(self.kpi_thresholds.items())),
        }

    def fingerprint(self) -> str:
        """Return a stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_dashboard_config(path: Path | str) -> DashboardConfig:
    """Load dashboard-output configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise DashboardConfigurationError(f"Dashboard configuration not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DashboardConfigurationError(f"Dashboard YAML is invalid: {config_path}") from exc
    if not isinstance(raw, dict):
        raise DashboardConfigurationError("Dashboard configuration root must be a mapping.")
    return parse_dashboard_config(raw)


def parse_dashboard_config(raw: dict[str, Any]) -> DashboardConfig:
    """Validate a raw dashboard-output configuration mapping."""
    settings_raw = _section(raw, "dashboard_outputs")
    inputs_raw = _section(raw, "input_options")
    semantic_raw = _section(raw, "semantic_model")
    thresholds_raw = _section(raw, "kpi_thresholds")
    formats = _strings(settings_raw.get("export_format"), "dashboard_outputs.export_format")
    if len(formats) != len(set(formats)):
        raise DashboardConfigurationError("Duplicate export formats are not allowed.")
    unsupported = set(formats) - SUPPORTED_EXPORT_FORMATS
    if unsupported:
        raise DashboardConfigurationError(f"Unsupported dashboard export formats: {sorted(unsupported)}")
    unknown_inputs = set(inputs_raw) - {"require_disruption_input", "require_monitoring_input", *OPTIONAL_FLAGS}
    if unknown_inputs:
        raise DashboardConfigurationError(f"Unsupported input options: {sorted(unknown_inputs)}")
    start = _date(semantic_raw.get("date_table_start"), "semantic_model.date_table_start")
    end = _date(semantic_raw.get("date_table_end"), "semantic_model.date_table_end")
    if end < start:
        raise DashboardConfigurationError("semantic_model.date_table_end must be on or after start.")
    timezone = _string(semantic_raw.get("timezone"), "semantic_model.timezone")
    try:
        zoneinfo.ZoneInfo(timezone)
    except zoneinfo.ZoneInfoNotFoundError as exc:
        raise DashboardConfigurationError(f"Unsupported semantic model timezone: {timezone}") from exc
    thresholds = {name: _ratio(value, f"kpi_thresholds.{name}") for name, value in thresholds_raw.items()}
    return DashboardConfig(
        settings=DashboardSettings(
            output_root=_root(settings_raw.get("output_root"), ("dashboard", "outputs")),
            report_root=_root(settings_raw.get("report_root"), ("reports", "dashboard_outputs")),
            overwrite=_bool(settings_raw.get("overwrite"), "dashboard_outputs.overwrite"),
            seed=_non_negative_int(settings_raw.get("seed"), "dashboard_outputs.seed"),
            export_format=tuple(formats),
            include_powerbi_model_spec=_bool(
                settings_raw.get("include_powerbi_model_spec"), "dashboard_outputs.include_powerbi_model_spec"
            ),
            include_measure_catalogue=_bool(
                settings_raw.get("include_measure_catalogue"), "dashboard_outputs.include_measure_catalogue"
            ),
            include_page_specs=_bool(settings_raw.get("include_page_specs"), "dashboard_outputs.include_page_specs"),
            include_data_dictionary=_bool(
                settings_raw.get("include_data_dictionary"), "dashboard_outputs.include_data_dictionary"
            ),
            maximum_example_records=_positive_int(
                settings_raw.get("maximum_example_records"), "dashboard_outputs.maximum_example_records"
            ),
        ),
        input_options=InputOptions(
            require_disruption_input=_bool(inputs_raw.get("require_disruption_input"), "require_disruption_input"),
            require_monitoring_input=_bool(inputs_raw.get("require_monitoring_input"), "require_monitoring_input"),
            use_passenger_forecast=_bool(inputs_raw.get("use_passenger_forecast"), "use_passenger_forecast"),
            use_delay_prediction=_bool(inputs_raw.get("use_delay_prediction"), "use_delay_prediction"),
            use_maintenance_analytics=_bool(inputs_raw.get("use_maintenance_analytics"), "use_maintenance_analytics"),
            use_genai_assistant=_bool(inputs_raw.get("use_genai_assistant"), "use_genai_assistant"),
        ),
        semantic_model=SemanticModelSettings(
            model_name=_string(semantic_raw.get("model_name"), "semantic_model.model_name"),
            date_table_start=start,
            date_table_end=end,
            currency_code=_currency(semantic_raw.get("currency_code")),
            timezone=timezone,
            surrogate_key_prefix=_string(semantic_raw.get("surrogate_key_prefix"), "surrogate_key_prefix"),
            unknown_member_label=_string(semantic_raw.get("unknown_member_label"), "unknown_member_label"),
        ),
        kpi_thresholds=dict(sorted(thresholds.items())),
    )


def with_overrides(
    config: DashboardConfig,
    *,
    output_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool | None = None,
) -> DashboardConfig:
    """Return a dashboard config with CLI overrides applied."""
    settings = config.settings
    return DashboardConfig(
        settings=DashboardSettings(
            **{
                **settings.__dict__,
                "output_root": output_root if output_root is not None else settings.output_root,
                "report_root": report_root if report_root is not None else settings.report_root,
                "seed": seed if seed is not None else settings.seed,
                "overwrite": overwrite if overwrite is not None else settings.overwrite,
            }
        ),
        input_options=config.input_options,
        semantic_model=config.semantic_model,
        kpi_thresholds=config.kpi_thresholds,
    )


def build_dashboard_run_id(
    config: DashboardConfig,
    validation_run_id: str,
    disruption_run_id: str,
    monitoring_run_id: str,
    optional_run_ids: tuple[str | None, ...],
    package_version: str,
    explicit_run_id: str | None = None,
) -> str:
    """Build a deterministic dashboard run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise DashboardConfigurationError(
                "dashboard_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = (
        f"{validation_run_id}|{disruption_run_id}|{monitoring_run_id}|"
        f"{optional_run_ids}|{package_version}|{config.fingerprint()}"
    )
    return f"dashboard-{validation_run_id}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _section(raw: object, key: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get(key), dict):
        raise DashboardConfigurationError(f"{key} must be a mapping.")
    value = raw[key]
    return dict(value)


def _strings(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise DashboardConfigurationError(f"{label} must contain non-empty strings.")
    return raw


def _string(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise DashboardConfigurationError(f"{label} must be a non-empty string.")
    return raw


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise DashboardConfigurationError(f"{label} must be boolean.")
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0 or raw > 10_000:
        raise DashboardConfigurationError(f"{label} must be a positive integer no greater than 10000.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise DashboardConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _ratio(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or not 0 <= float(raw) <= 1:
        raise DashboardConfigurationError(f"{label} must be in [0, 1].")
    return float(raw)


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    if not isinstance(raw, str) or not raw:
        raise DashboardConfigurationError(f"{'/'.join(allowed_prefix)} path must be a non-empty string.")
    path = Path(raw)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise DashboardConfigurationError(f"{raw} must remain under {'/'.join(allowed_prefix)}.")
    return path


def _date(raw: object, label: str) -> date:
    if not isinstance(raw, str):
        raise DashboardConfigurationError(f"{label} must be an ISO date string.")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise DashboardConfigurationError(f"{label} must be an ISO date string.") from exc


def _currency(raw: object) -> str:
    value = _string(raw, "semantic_model.currency_code")
    if not re.fullmatch(r"[A-Z]{3}", value):
        raise DashboardConfigurationError("semantic_model.currency_code must be a three-letter ISO-style code.")
    return value
