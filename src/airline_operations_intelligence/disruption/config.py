"""Configuration parsing for disruption scoring."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import DisruptionScoringConfigurationError
from airline_operations_intelligence.disruption.contracts import ScoreBand

DEFAULT_DISRUPTION_SCORING_CONFIG_PATH = Path("configs/disruption_scoring.yaml")
SUPPORTED_STATUSES = {"passed", "passed_with_warnings"}
COMPONENTS = {
    "delay",
    "weather",
    "airport_events",
    "crew",
    "aircraft_health",
    "passenger_pressure",
    "network_reactionary",
}


@dataclass(frozen=True)
class DisruptionSettings:
    """Validated disruption scoring settings."""

    output_root: Path
    report_root: Path
    overwrite: bool
    seed: int
    accepted_validation_status: tuple[str, ...]
    enable_forward_risk_score: bool
    enable_retrospective_score: bool
    maximum_alerts_per_run: int
    use_passenger_forecast: bool
    use_delay_prediction: bool
    use_maintenance_analytics: bool
    require_optional_inputs: bool
    risk_bands: tuple[ScoreBand, ...]
    recovery_priority: tuple[ScoreBand, ...]
    component_weights: dict[str, float]
    thresholds: dict[str, float]


@dataclass(frozen=True)
class DisruptionScoringConfig:
    """Top-level disruption scoring config."""

    settings: DisruptionSettings

    def effective_configuration(self) -> dict[str, Any]:
        """Return deterministic JSON-serialisable configuration."""
        s = self.settings
        return {
            "disruption_scoring": {
                "output_root": s.output_root.as_posix(),
                "report_root": s.report_root.as_posix(),
                "overwrite": s.overwrite,
                "seed": s.seed,
                "accepted_validation_status": list(s.accepted_validation_status),
                "enable_forward_risk_score": s.enable_forward_risk_score,
                "enable_retrospective_score": s.enable_retrospective_score,
                "maximum_alerts_per_run": s.maximum_alerts_per_run,
            },
            "input_options": {
                "use_passenger_forecast": s.use_passenger_forecast,
                "use_delay_prediction": s.use_delay_prediction,
                "use_maintenance_analytics": s.use_maintenance_analytics,
                "require_optional_inputs": s.require_optional_inputs,
            },
            "risk_bands": _bands_payload(s.risk_bands),
            "recovery_priority": _bands_payload(s.recovery_priority),
            "component_weights": s.component_weights,
            "thresholds": s.thresholds,
        }

    def fingerprint(self) -> str:
        """Return stable configuration fingerprint."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_disruption_config(path: Path | str) -> DisruptionScoringConfig:
    """Load disruption scoring configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise DisruptionScoringConfigurationError(f"Disruption scoring configuration not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DisruptionScoringConfigurationError(f"Disruption scoring YAML is invalid: {config_path}") from exc
    if not isinstance(raw, dict):
        raise DisruptionScoringConfigurationError("Disruption scoring configuration root must be a mapping.")
    return parse_disruption_config(raw)


def parse_disruption_config(raw: dict[str, Any]) -> DisruptionScoringConfig:
    """Validate raw disruption scoring configuration."""
    scoring = _section(raw, "disruption_scoring")
    input_options = _section(raw, "input_options")
    statuses = tuple(_choices(_strings(scoring.get("accepted_validation_status"), "accepted_validation_status")))
    _reject_duplicates(statuses, "accepted validation statuses")
    weights = _weights(_section(raw, "component_weights"))
    settings = DisruptionSettings(
        output_root=_root(scoring.get("output_root"), ("outputs", "disruption_scoring")),
        report_root=_root(scoring.get("report_root"), ("reports", "disruption_scoring")),
        overwrite=_bool(scoring.get("overwrite"), "overwrite"),
        seed=_non_negative_int(scoring.get("seed"), "seed"),
        accepted_validation_status=statuses,
        enable_forward_risk_score=_bool(scoring.get("enable_forward_risk_score"), "enable_forward_risk_score"),
        enable_retrospective_score=_bool(scoring.get("enable_retrospective_score"), "enable_retrospective_score"),
        maximum_alerts_per_run=_positive_int(scoring.get("maximum_alerts_per_run"), "maximum_alerts_per_run"),
        use_passenger_forecast=_bool(input_options.get("use_passenger_forecast"), "use_passenger_forecast"),
        use_delay_prediction=_bool(input_options.get("use_delay_prediction"), "use_delay_prediction"),
        use_maintenance_analytics=_bool(input_options.get("use_maintenance_analytics"), "use_maintenance_analytics"),
        require_optional_inputs=_bool(input_options.get("require_optional_inputs"), "require_optional_inputs"),
        risk_bands=_bands(_section(raw, "risk_bands")),
        recovery_priority=_bands(_section(raw, "recovery_priority")),
        component_weights=weights,
        thresholds={
            name: _non_negative_float(value, f"thresholds.{name}")
            for name, value in _section(raw, "thresholds").items()
        },
    )
    if not settings.enable_forward_risk_score and not settings.enable_retrospective_score:
        raise DisruptionScoringConfigurationError("At least one disruption score type must be enabled.")
    return DisruptionScoringConfig(settings=settings)


def with_overrides(
    config: DisruptionScoringConfig,
    *,
    output_root: Path | None = None,
    report_root: Path | None = None,
    seed: int | None = None,
    overwrite: bool | None = None,
) -> DisruptionScoringConfig:
    """Return config with CLI overrides applied."""
    s = config.settings
    return DisruptionScoringConfig(
        settings=DisruptionSettings(
            **{
                **s.__dict__,
                "output_root": output_root if output_root is not None else s.output_root,
                "report_root": report_root if report_root is not None else s.report_root,
                "seed": seed if seed is not None else s.seed,
                "overwrite": overwrite if overwrite is not None else s.overwrite,
            }
        )
    )


def build_disruption_run_id(
    config: DisruptionScoringConfig,
    validation_run_id: str,
    optional_run_ids: tuple[str | None, str | None, str | None],
    package_version: str,
    explicit_run_id: str | None = None,
) -> str:
    """Build deterministic disruption scoring run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", explicit_run_id):
            raise DisruptionScoringConfigurationError(
                "disruption_run_id may only contain letters, numbers, dots, dashes, and underscores."
            )
        return explicit_run_id
    payload = f"{validation_run_id}|{optional_run_ids}|{package_version}|{config.fingerprint()}"
    return f"disruption-{validation_run_id}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:10]}"


def _bands(raw: dict[str, Any]) -> tuple[ScoreBand, ...]:
    bands = tuple(
        ScoreBand(
            name=name,
            minimum_score=_probability(_section(value, name).get("minimum_score"), f"{name}.minimum_score"),
            maximum_score=_probability(_section(value, name).get("maximum_score"), f"{name}.maximum_score"),
        )
        for name, value in sorted(
            raw.items(), key=lambda item: _probability(_section(item[1], item[0]).get("minimum_score"), item[0])
        )
    )
    if not bands or abs(bands[0].minimum_score) > 0.0001 or abs(bands[-1].maximum_score - 1.0) > 0.0001:
        raise DisruptionScoringConfigurationError("Score bands must cover 0.0 through 1.0.")
    previous = 0.0
    for band in bands:
        if abs(band.minimum_score - previous) > 0.0001 or band.maximum_score <= band.minimum_score:
            raise DisruptionScoringConfigurationError("Score bands must be contiguous and increasing.")
        previous = band.maximum_score
    return bands


def _weights(raw: dict[str, Any]) -> dict[str, float]:
    if set(raw) != COMPONENTS:
        raise DisruptionScoringConfigurationError("component_weights must contain supported component keys exactly.")
    weights = {name: _non_negative_float(value, f"component_weights.{name}") for name, value in raw.items()}
    total = sum(weights.values())
    if total <= 0 or abs(total - 1.0) > 0.0001:
        raise DisruptionScoringConfigurationError("component_weights must sum to 1.0.")
    return dict(sorted(weights.items()))


def _bands_payload(bands: tuple[ScoreBand, ...]) -> dict[str, dict[str, float]]:
    return {band.name: {"minimum_score": band.minimum_score, "maximum_score": band.maximum_score} for band in bands}


def _section(raw: object, key: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DisruptionScoringConfigurationError(f"{key} must be a mapping.")
    value = raw.get(key) if key in raw else raw
    if not isinstance(value, dict):
        raise DisruptionScoringConfigurationError(f"{key} must be a mapping.")
    return value


def _strings(raw: object, label: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise DisruptionScoringConfigurationError(f"{label} must contain non-empty strings.")
    return raw


def _choices(values: list[str]) -> list[str]:
    for value in values:
        if value not in SUPPORTED_STATUSES:
            raise DisruptionScoringConfigurationError(f"Unsupported validation status: {value}")
    return values


def _reject_duplicates(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise DisruptionScoringConfigurationError(f"Duplicate {label} are not allowed.")


def _bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise DisruptionScoringConfigurationError(f"{label} must be boolean.")
    return raw


def _positive_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw <= 0:
        raise DisruptionScoringConfigurationError(f"{label} must be a positive integer.")
    return raw


def _non_negative_int(raw: object, label: str) -> int:
    if not isinstance(raw, int) or raw < 0:
        raise DisruptionScoringConfigurationError(f"{label} must be a non-negative integer.")
    return raw


def _non_negative_float(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or float(raw) < 0:
        raise DisruptionScoringConfigurationError(f"{label} must be a non-negative number.")
    return float(raw)


def _probability(raw: object, label: str) -> float:
    if not isinstance(raw, int | float) or not 0 <= float(raw) <= 1:
        raise DisruptionScoringConfigurationError(f"{label} must be a probability between 0 and 1.")
    return float(raw)


def _root(raw: object, allowed_prefix: tuple[str, ...]) -> Path:
    if not isinstance(raw, str) or not raw:
        raise DisruptionScoringConfigurationError(f"{'/'.join(allowed_prefix)} path must be a non-empty string.")
    path = Path(raw)
    if path.is_absolute() or path.parts[: len(allowed_prefix)] != allowed_prefix:
        raise DisruptionScoringConfigurationError(f"{raw} must remain under {'/'.join(allowed_prefix)}.")
    return path
