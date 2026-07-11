from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


def test_azure_mapping_config_is_reference_only_and_complete() -> None:
    config = _load_mapping()
    mapping = config["azure_mapping"]
    services = {service for values in config["services"].values() for service in values}
    zones = config["data_zones"]

    assert mapping["deployment_mode"] == "reference_only"
    assert mapping["deployment_allowed"] is False
    assert mapping["environments"] == ["dev", "test", "prod"]
    assert len(mapping["environments"]) == len(set(mapping["environments"]))
    assert set(zones) == {"raw", "interim", "processed", "analytics_outputs", "reporting", "dashboard"}
    assert {zone["local_path"] for zone in zones.values()} == {
        "data/raw",
        "data/interim",
        "data/processed",
        "outputs",
        "reports",
        "dashboard/outputs",
    }
    assert {
        "Azure Event Hubs",
        "Azure Data Lake Storage Gen2",
        "Azure Machine Learning",
        "Azure AI Foundry",
        "Azure OpenAI",
        "Azure Monitor",
        "Microsoft Purview",
        "Microsoft Entra ID",
        "Azure Key Vault",
        "Microsoft Power BI",
        "Microsoft Fabric Lakehouse",
    } <= services


def test_static_validator_passes_and_patterns_detect_unsafe_text() -> None:
    validator = _validator_module()

    assert validator.validate(_repo_root()) == []
    assert validator._forbidden_patterns()["tf-apply"].search("terraform   apply")
    assert validator._forbidden_patterns()["az-login"].search("az login")
    assert validator._guid_pattern().search("11111111-2222-3333-4444-555555555555")


def test_required_azure_docs_diagrams_and_iac_exist() -> None:
    validator = _validator_module()
    root = _repo_root()

    for relative in (*validator.REQUIRED_DOCS, *validator.REQUIRED_DIAGRAMS, *validator.REQUIRED_IAC):
        assert (root / relative).is_file(), relative
    for relative in validator.REQUIRED_IAC:
        text = (root / relative).read_text(encoding="utf-8").lower()
        assert "reference only" in text
        assert "non-deploying" in text
        assert "no azure resources are provisioned" in text


def _load_mapping() -> dict:
    return yaml.safe_load((_repo_root() / "configs/azure_mapping.yaml").read_text(encoding="utf-8"))


def _validator_module():
    path = _repo_root() / "scripts/validate_azure_architecture.py"
    spec = importlib.util.spec_from_file_location("validate_azure_architecture", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
