"""Configuration loading and validation for the local-first foundation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import ConfigurationError

DEFAULT_CONFIG_PATH = Path("configs/platform.yaml")
DEFAULT_RANDOM_SEED = 1729


@dataclass(frozen=True)
class PlatformConfig:
    """Validated non-secret platform configuration."""

    project_name: str
    environment: str
    version: str
    random_seed: int
    logging_level: str
    paths: dict[str, Path]
    azure_service_mapping: dict[str, str]
    governance: dict[str, bool]


def load_platform_config(path: Path | str = DEFAULT_CONFIG_PATH) -> PlatformConfig:
    """Load and validate the baseline platform configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Configuration file is not valid YAML: {config_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping.")

    return _parse_config(raw)


def _parse_config(raw: dict[str, Any]) -> PlatformConfig:
    project = _require_mapping(raw, "project")
    runtime = _require_mapping(raw, "runtime")
    paths = _require_mapping(raw, "paths")
    service_mapping = _require_mapping(raw, "azure_service_mapping")
    governance = _require_mapping(raw, "governance")

    project_name = _require_str(project, "name")
    environment = _require_str(project, "environment")
    version = _require_str(project, "version")
    logging_level = _require_str(runtime, "logging_level")
    random_seed = runtime.get("random_seed", DEFAULT_RANDOM_SEED)
    if not isinstance(random_seed, int):
        raise ConfigurationError("runtime.random_seed must be an integer.")

    parsed_paths = {key: Path(_require_str(paths, key)) for key in paths}
    parsed_mapping = {key: _expect_str(value, f"azure_service_mapping.{key}") for key, value in service_mapping.items()}
    parsed_governance = {key: _expect_bool(value, f"governance.{key}") for key, value in governance.items()}

    _validate_governance(parsed_governance)

    return PlatformConfig(
        project_name=project_name,
        environment=environment,
        version=version,
        random_seed=random_seed,
        logging_level=logging_level,
        paths=parsed_paths,
        azure_service_mapping=parsed_mapping,
        governance=parsed_governance,
    )


def _require_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"{key} must be present and must be a mapping.")
    return value


def _require_str(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    return _expect_str(value, key)


def _expect_str(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{key} must be a non-empty string.")
    return value


def _expect_bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _validate_governance(governance: dict[str, bool]) -> None:
    required_flags = {
        "synthetic_data_only": True,
        "allow_personal_data": False,
        "require_human_review_for_consequential_decisions": True,
        "safety_critical_use_allowed": False,
    }
    for key, expected in required_flags.items():
        if governance.get(key) is not expected:
            raise ConfigurationError(f"governance.{key} must be {expected!s}.")
