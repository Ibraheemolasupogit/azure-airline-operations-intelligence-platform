from pathlib import Path

import pytest

from airline_operations_intelligence.common.config import DEFAULT_RANDOM_SEED, load_platform_config
from airline_operations_intelligence.common.exceptions import ConfigurationError


def test_load_platform_config_reads_baseline_config() -> None:
    config = load_platform_config("configs/platform.yaml")

    assert config.project_name == "azure-airline-operations-intelligence-platform"
    assert config.environment == "local"
    assert config.random_seed == 1729
    assert config.paths["data_raw"] == Path("data/raw")
    assert config.azure_service_mapping["event_ingestion"] == "Azure Event Hubs"


def test_config_default_seed_is_deterministic_when_omitted(tmp_path: Path) -> None:
    config_file = tmp_path / "platform.yaml"
    config_file.write_text(
        """
project:
  name: demo
  environment: local
  version: 0.1.0
runtime:
  logging_level: INFO
paths:
  data_raw: data/raw
azure_service_mapping:
  event_ingestion: Azure Event Hubs
governance:
  synthetic_data_only: true
  allow_personal_data: false
  require_human_review_for_consequential_decisions: true
  safety_critical_use_allowed: false
""",
        encoding="utf-8",
    )

    config = load_platform_config(config_file)

    assert config.random_seed == DEFAULT_RANDOM_SEED


def test_missing_config_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_platform_config(tmp_path / "missing.yaml")


def test_malformed_config_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "platform.yaml"
    config_file.write_text("project: [broken", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="not valid YAML"):
        load_platform_config(config_file)


def test_governance_config_rejects_personal_data(tmp_path: Path) -> None:
    config_file = tmp_path / "platform.yaml"
    config_file.write_text(
        """
project:
  name: demo
  environment: local
  version: 0.1.0
runtime:
  random_seed: 1
  logging_level: INFO
paths:
  data_raw: data/raw
azure_service_mapping:
  event_ingestion: Azure Event Hubs
governance:
  synthetic_data_only: true
  allow_personal_data: true
  require_human_review_for_consequential_decisions: true
  safety_critical_use_allowed: false
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="allow_personal_data"):
        load_platform_config(config_file)
