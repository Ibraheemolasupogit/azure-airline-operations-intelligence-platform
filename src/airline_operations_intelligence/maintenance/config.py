"""Configuration parsing for aircraft-health maintenance analytics."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import MaintenanceAnalyticsConfigurationError

DEFAULT_MAINTENANCE_ANALYTICS_CONFIG_PATH = Path("configs/maintenance_analytics.yaml")
SUPPORTED_STATUSES = {"passed", "passed_with_warnings"}
TELEMETRY_FIELDS = {
    "engine_1_vibration",
    "engine_2_vibration",
    "engine_1_temperature_c",
    "engine_2_temperature_c",
    "hydraulic_pressure_psi",
    "oil_pressure_psi",
    "brake_temperature_c",
}
WEIGHT_KEYS = {
    "sensor_thresholds",
    "telemetry_anomaly",
    "degradation_trend",
    "fault_code",
    "utilisation",
    "recent_delay_or_operational_context",
}


@dataclass(frozen=True)
class TelemetryBound:
    """Validated telemetry warning and critical bounds."""

    warning_min: float | None
    warning_max: float | None
    critical_min: float | None
    critical_max: float | None


@dataclass(frozen=True)
class MaintenanceSettings:
    """Validated maintenance analytics settings."""

    output_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    accepted_validation_status: tuple[str, ...]
    risk_score_thresholds: dict[str, float]
    alert_thresholds: dict[str, float]
    rolling_windows: tuple[int, ...]
    enable_statistical_anomaly_detection: bool
    enable_flight_level_risk: bool
    minimum_aircraft_observations: int
    maximum_alerts_per_aircraft: int
    telemetry_bounds: dict[str, TelemetryBound]
    risk_weights: dict[str, float]


@dataclass(frozen=True)
class MaintenanceAnalyticsConfig:
    """Top-level maintenance analytics config."""

    settings: MaintenanceSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "maintenance_analytics": {
                "output_root": s.output_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "accepted_validation_status": list(s.accepted_validation_status),
                "risk_score_thresholds": s.risk_score_thresholds,
                "alert_thresholds": s.alert_thresholds,
                "rolling_windows": list(s.rolling_windows),
                "enable_statistical_anomaly_detection": s.enable_statistical_anomaly_detection,
                "enable_flight_level_risk": s.enable_flight_level_risk,
                "minimum_aircraft_observations": s.minimum_aircraft_observations,
                "maximum_alerts_per_aircraft": s.maximum_alerts_per_aircraft,
            },
            "telemetry_bounds": {
                name: {
                    "warning_min": bound.warning_min,
                    "warning_max": bound.warning_max,
                    "critical_min": bound.critical_min,
                    "critical_max": bound.critical_max,
                }
                for name, bound in sorted(s.telemetry_bounds.items())
            },
            "risk_weights": s.risk_weights,
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_maintenance_config(path: Path | str) -> MaintenanceAnalyticsConfig:
    """Load maintenance analytics configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise MaintenanceAnalyticsConfigurationError(f"Maintenance analytics configuration not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MaintenanceAnalyticsConfigurationError(f"Maintenance analytics YAML is invalid: {config_path}") from exc
    if not isinstance(raw, dict):
        raise MaintenanceAnalyticsConfigurationError("Maintenance analytics configuration root must be a mapping.")
    return parse_maintenance_config(raw)


def parse_maintenance_config(raw: dict[str, Any]) -> MaintenanceAnalyticsConfig:
    """Validate raw maintenance analytics configuration."""
    analytics = _section(raw, "maintenance_analytics")
    statuses = tuple(_choices(_strings(analytics.get("accepted_validation_status"), "accepted_validation_status")))
    _reject_duplicates(statuses, "accepted validation statuses")
    risk_thresholds = _thresholds(_section(analytics, "risk_score_thresholds"), ("low", "medium", "high"))
    alert_thresholds = _thresholds(_section(analytics, "alert_thresholds"), ("advisory", "watch", "action_recommended"))
    windows = tuple(
        sorted(
            {
                _positive_int(value, "rolling_windows")
                for value in _list(analytics.get("rolling_windows"), "rolling_windows")
            }
        )
    )
    if len(windows) != len(_list(analytics.get("rolling_windows"), "rolling_windows")):
        raise MaintenanceAnalyticsConfigurationError("rolling_windows must not contain duplicates.")
    bounds = _telemetry_bounds(_section(raw, "telemetry_bounds"))
    weights = _weights(_section(raw, "risk_weights"))
    settings = MaintenanceSettings(
        output_root=_root(analytics.get("output_root"), ("outputs", "maintenance_analytics")),
        report_root=_root(analytics.get("report_root"), ("reports", "maintenance_analytics")),
        overwrite=_bool(analytics.get("overwrite"), "overwrite"),
        seed=_non_negative_int(analytics.get("seed"), "seed"),
        accepted_validation_status=statuses,
        risk_score_thresholds=risk_thresholds,
        alert_thresholds=alert_thresholds,
        rolling_windows=windows,
        enable_statistical_anomaly_detection=_bool(
            analytics.get("enable_statistical_anomaly_detection"), "enable_statistical_anomaly_detection"
        ),
        enable_flight_level_risk=_bool(analytics.get("enable_flight_level_risk"), "enable_flight_level_risk"),
        minimum_aircraft_observations=_positive_int(
            analytics.get("minimum_aircraft_observations"), "minimum_aircraft_observations"
        ),
        maximum_alerts_per_aircraft=_positive_int(
            analytics.get("maximum_alerts_per_aircraft"), "maximum_alerts_per_aircraft"
        ),
        telemetry_bounds=bounds,
        risk_weights=weights,
    )
    return MaintenanceAnalyticsConfig(settings=settings)


def with_overrides(
    config: MaintenanceAnalyticsConfig,
    *,
    output_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool | None = None,
) -> MaintenanceAnalyticsConfig:
    """Return config with CLI overrides applied."""
    s = config.settings
    return MaintenanceAnalyticsConfig(
        settings=MaintenanceSettings(
            **{
                **s.__dict__,
                "output_root": output_root if output_root is not None else s.output_root,
                "report_root": report_root if report_root is not None else s.report_root,
                "seed": seed if seed is not None else s.seed,
                "overwrite": overwrite if overwrite is not None else s.overwrite,
            }
        )
    )


def build_maintenance_run_id(
    config: MaintenanceAnalyticsConfig, validation_run_id: str, package_version: str, explicit_run_id: str | None = None
) -> str:
    """Build deterministic maintenance analytics run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise MaintenanceAnalyticsConfigurationError(
                "maintenance_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = f"{validation_run_id}|{package_version}|{config.fingerprint()}"
    return f"maintenance-{validation_run_id}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _telemetry_bounds(raw: dict[str, Any]) -> dict[str, TelemetryBound]:
    unknown = set(raw) - TELEMETRY_FIELDS
    if unknown:
        raise MaintenanceAnalyticsConfigurationError(f"Unknown telemetry fields: {', '.join(sorted(unknown))}")
    bounds: dict[str, TelemetryBound] = {}
    for name in sorted(TELEMETRY_FIELDS):
        values = _section(raw, name)
        bound = TelemetryBound(
            warning_min=_optional_float(values.get("warning_min"), f"{name}.warning_min"),
            warning_max=_optional_float(values.get("warning_max"), f"{name}.warning_max"),
            critical_min=_optional_float(values.get("critical_min"), f"{name}.critical_min"),
            critical_max=_optional_float(values.get("critical_max"), f"{name}.critical_max"),
        )
        for lower, upper, label in (
            (bound.warning_min, bound.warning_max, "warning"),
            (bound.critical_min, bound.critical_max, "critical"),
        ):
            if lower is not None and upper is not None and lower >= upper:
                raise MaintenanceAnalyticsConfigurationError(f"{name} {label} min must be below max.")
        bounds[name] = bound
    return bounds


def _weights(raw: dict[str, Any]) -> dict[str, float]:
    if set(raw) != WEIGHT_KEYS:
        raise MaintenanceAnalyticsConfigurationError("risk_weights must contain the supported component keys exactly.")
    weights = {name: _non_negative_float(value, f"risk_weights.{name}") for name, value in raw.items()}
    total = sum(weights.values())
    if abs(total - 1.0) > 0.0001:
        raise MaintenanceAnalyticsConfigurationError("risk_weights must sum to 1.0.")
    return dict(sorted(weights.items()))


def _thresholds(raw: dict[str, Any], names: tuple[str, ...]) -> dict[str, float]:
    values = {name: _probability(raw.get(name), name) for name in names}
    ordered = [values[name] for name in names]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise MaintenanceAnalyticsConfigurationError(f"{', '.join(names)} thresholds must be monotonic.")
    return values


def _section(raw: object, key: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MaintenanceAnalyticsConfigurationError(f"{key} must be a mapping.")
    value = raw.get(key)
    if not isinstance(value, dict):
        raise MaintenanceAnalyticsConfigurationError(f"{key} must be a mapping.")
    return value


def _list(raw: object, label: str) -> list[Any]:
    if not isinstance(raw, list):
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be a list.")
    return raw


def _strings(raw: object, label: str) -> list[str]:
    values = _list(raw, label)
    if not all(isinstance(value, str) and value for value in values):
        raise MaintenanceAnalyticsConfigurationError(f"{label} must contain non-empty strings.")
    return values


def _choices(values: list[str]) -> list[str]:
    for value in values:
        if value not in SUPPORTED_STATUSES:
            raise MaintenanceAnalyticsConfigurationError(f"Unsupported validation status: {value}")
    return values


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise MaintenanceAnalyticsConfigurationError(f"Duplicate {label} are not allowed.")


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be boolean.")
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0:
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be a positive integer.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _non_negative_float(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or float(raw) < 0:
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be a non-negative number.")
    return float(raw)


def _optional_float(raw: object, label: str) -> float | None:
    if raw is None:
        return None
    if not isinstance(raw, int | float):
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be numeric when supplied.")
    return float(raw)


def _probability(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or not 0 <= float(raw) <= 1:
        raise MaintenanceAnalyticsConfigurationError(f"{label} must be a probability between 0 and 1.")
    return float(raw)


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    if not isinstance(raw, str) or not raw:
        raise MaintenanceAnalyticsConfigurationError(f"{'/'.join(allowed_prefix)} path must be a non-empty string.")
    path = Path(raw)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise MaintenanceAnalyticsConfigurationError(f"{raw} must remain under {'/'.join(allowed_prefix)}.")
    return path
