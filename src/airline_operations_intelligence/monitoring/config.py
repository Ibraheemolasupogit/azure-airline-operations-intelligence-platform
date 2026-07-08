"""Configuration parsing for local platform monitoring."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import MonitoringConfigurationError
from airline_operations_intelligence.monitoring.contracts import DOMAINS, SEVERITIES

DEFAULT_MONITORING_CONFIG_PATH = Path("configs/monitoring.yaml")
SUPPORTED_STATUSES = {"passed", "passed_with_warnings", "completed", "succeeded"}


@dataclass(frozen=True)
class MonitoringSettings:
    """Validated monitoring settings."""

    output_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    accepted_statuses: tuple[str, ...]
    maximum_alerts_per_run: int
    enable_drift_checks: bool
    enable_model_metric_checks: bool
    enable_data_quality_checks: bool
    enable_lineage_checks: bool
    enable_runtime_checks: bool
    thresholds: dict[str, float | str]
    severity_policy: dict[str, int]
    monitoring_domains: dict[str, bool]


@dataclass(frozen=True)
class MonitoringConfig:
    """Top-level monitoring configuration."""

    settings: MonitoringSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "monitoring": {
                "output_root": s.output_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "accepted_statuses": list(s.accepted_statuses),
                "maximum_alerts_per_run": s.maximum_alerts_per_run,
                "enable_drift_checks": s.enable_drift_checks,
                "enable_model_metric_checks": s.enable_model_metric_checks,
                "enable_data_quality_checks": s.enable_data_quality_checks,
                "enable_lineage_checks": s.enable_lineage_checks,
                "enable_runtime_checks": s.enable_runtime_checks,
            },
            "thresholds": dict(sorted(s.thresholds.items())),
            "severity_policy": dict(sorted(s.severity_policy.items())),
            "monitoring_domains": dict(sorted(s.monitoring_domains.items())),
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_monitoring_config(path: Path | str) -> MonitoringConfig:
    """Load monitoring configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise MonitoringConfigurationError(f"Monitoring configuration not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MonitoringConfigurationError(f"Monitoring YAML is invalid: {config_path}") from exc
    if not isinstance(raw, dict):
        raise MonitoringConfigurationError("Monitoring configuration root must be a mapping.")
    return parse_monitoring_config(raw)


def parse_monitoring_config(raw: dict[str, Any]) -> MonitoringConfig:
    """Validate raw monitoring configuration."""
    monitoring = _section(raw, "monitoring")
    thresholds = _thresholds(_section(raw, "thresholds"))
    severity_policy = _severity_policy(_section(raw, "severity_policy"))
    domains = _domains(_section(raw, "monitoring_domains"))
    statuses = tuple(_strings(monitoring.get("accepted_statuses"), "accepted_statuses"))
    _reject_duplicates(statuses, "accepted statuses")
    for status in statuses:
        if status not in SUPPORTED_STATUSES:
            raise MonitoringConfigurationError(f"Unsupported monitoring accepted status: {status}")
    settings = MonitoringSettings(
        output_root=_root(monitoring.get("output_root"), ("outputs", "monitoring")),
        report_root=_root(monitoring.get("report_root"), ("reports", "monitoring")),
        overwrite=_bool(monitoring.get("overwrite"), "overwrite"),
        seed=_non_negative_int(monitoring.get("seed"), "seed"),
        accepted_statuses=statuses,
        maximum_alerts_per_run=_positive_int(monitoring.get("maximum_alerts_per_run"), "maximum_alerts_per_run"),
        enable_drift_checks=_bool(monitoring.get("enable_drift_checks"), "enable_drift_checks"),
        enable_model_metric_checks=_bool(monitoring.get("enable_model_metric_checks"), "enable_model_metric_checks"),
        enable_data_quality_checks=_bool(monitoring.get("enable_data_quality_checks"), "enable_data_quality_checks"),
        enable_lineage_checks=_bool(monitoring.get("enable_lineage_checks"), "enable_lineage_checks"),
        enable_runtime_checks=_bool(monitoring.get("enable_runtime_checks"), "enable_runtime_checks"),
        thresholds=thresholds,
        severity_policy=severity_policy,
        monitoring_domains=domains,
    )
    _validate_threshold_relationships(settings.thresholds)
    return MonitoringConfig(settings=settings)


def with_overrides(
    config: MonitoringConfig,
    *,
    output_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool | None = None,
) -> MonitoringConfig:
    """Return config with CLI overrides applied."""
    s = config.settings
    return MonitoringConfig(
        settings=MonitoringSettings(
            **{
                **s.__dict__,
                "output_root": output_root if output_root is not None else s.output_root,
                "report_root": report_root if report_root is not None else s.report_root,
                "seed": seed if seed is not None else s.seed,
                "overwrite": overwrite if overwrite is not None else s.overwrite,
            }
        )
    )


def build_monitoring_run_id(
    config: MonitoringConfig,
    validation_run_id: str,
    optional_run_ids: tuple[str | None, str | None, str | None, str | None],
    baseline_run_id: str | None,
    package_version: str,
    explicit_run_id: str | None = None,
) -> str:
    """Build deterministic monitoring run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise MonitoringConfigurationError(
                "monitoring_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = f"{validation_run_id}|{optional_run_ids}|{baseline_run_id}|{package_version}|{config.fingerprint()}"
    return f"monitoring-{validation_run_id}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _section(raw: object, key: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MonitoringConfigurationError(f"{key} must be a mapping.")
    value = raw.get(key)
    if not isinstance(value, dict):
        raise MonitoringConfigurationError(f"{key} must be a mapping.")
    return value


def _strings(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise MonitoringConfigurationError(f"{label} must contain non-empty strings.")
    return raw


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise MonitoringConfigurationError(f"Duplicate {label} are not allowed.")


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise MonitoringConfigurationError(f"{label} must be boolean.")
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0:
        raise MonitoringConfigurationError(f"{label} must be a positive integer.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise MonitoringConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _non_negative_number(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or float(raw) < 0:
        raise MonitoringConfigurationError(f"{label} must be a non-negative number.")
    return float(raw)


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    if not isinstance(raw, str) or not raw:
        raise MonitoringConfigurationError(f"{'/'.join(allowed_prefix)} path must be a non-empty string.")
    path = Path(raw)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise MonitoringConfigurationError(f"{raw} must remain under {'/'.join(allowed_prefix)}.")
    return path


def _thresholds(raw: dict[str, Any]) -> dict[str, float | str]:
    thresholds: dict[str, float | str] = {}
    for name, value in raw.items():
        if name.endswith("_severity"):
            if value not in SEVERITIES:
                raise MonitoringConfigurationError(f"thresholds.{name} must be a supported severity.")
            thresholds[name] = str(value)
        else:
            thresholds[name] = _non_negative_number(value, f"thresholds.{name}")
    return dict(sorted(thresholds.items()))


def _severity_policy(raw: dict[str, Any]) -> dict[str, int]:
    if set(raw) != set(SEVERITIES):
        raise MonitoringConfigurationError("severity_policy must define info, warning, high, and critical.")
    policy: dict[str, int] = {}
    for severity, value in raw.items():
        if not isinstance(value, int) or value < 0:
            raise MonitoringConfigurationError(f"severity_policy.{severity} must be a non-negative integer.")
        policy[severity] = value
    ordered = [policy[severity] for severity in SEVERITIES]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise MonitoringConfigurationError("severity_policy must be strictly increasing.")
    return dict(sorted(policy.items()))


def _domains(raw: dict[str, Any]) -> dict[str, bool]:
    if set(raw) != set(DOMAINS):
        raise MonitoringConfigurationError("monitoring_domains must contain supported domain keys exactly.")
    return {domain: _bool(raw[domain], f"monitoring_domains.{domain}") for domain in DOMAINS}


def _validate_threshold_relationships(thresholds: dict[str, float | str]) -> None:
    pairs = (
        ("validation_error_count_warning", "validation_error_count_critical"),
        ("invalid_record_rate_warning", "invalid_record_rate_critical"),
        ("max_runtime_seconds_warning", "max_runtime_seconds_critical"),
        ("passenger_forecast_wape_warning", "passenger_forecast_wape_critical"),
        ("drift_relative_change_warning", "drift_relative_change_critical"),
    )
    for warning_name, critical_name in pairs:
        warning = float(thresholds[warning_name])
        critical = float(thresholds[critical_name])
        if critical < warning:
            raise MonitoringConfigurationError(f"{critical_name} must be greater than or equal to {warning_name}.")
    if float(thresholds["delay_prediction_pr_auc_critical"]) > float(thresholds["delay_prediction_pr_auc_warning"]):
        raise MonitoringConfigurationError("delay PR-AUC critical threshold must be less than or equal to warning.")
