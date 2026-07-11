"""Static validation for Milestone 11 Azure architecture mapping."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "docs/azure/azure-target-architecture.md",
    "docs/azure/azure-service-mapping.md",
    "docs/azure/azure-environment-strategy.md",
    "docs/azure/azure-data-zone-mapping.md",
    "docs/azure/azure-security-governance.md",
    "docs/azure/azure-mlops-mapping.md",
    "docs/azure/azure-monitoring-observability.md",
    "docs/azure/azure-genai-foundry-mapping.md",
    "docs/azure/azure-powerbi-fabric-mapping.md",
    "docs/azure/azure-cost-considerations.md",
    "docs/azure/azure-deployment-boundaries.md",
    "docs/azure/azure-operational-runbook.md",
    "docs/milestones/milestone-11.md",
    "docs/architecture/azure-deployment-architecture.md",
    "docs/governance/azure-governance.md",
    "docs/operations/azure-architecture-review.md",
    "reports/architecture/azure-architecture-evidence.md",
)
REQUIRED_DIAGRAMS = (
    "diagrams/azure-target-architecture.mmd",
    "diagrams/azure-data-zones.mmd",
    "diagrams/azure-security-governance.mmd",
    "diagrams/azure-mlops-genai-monitoring.mmd",
)
REQUIRED_IAC = (
    "infra/README.md",
    "infra/bicep/README.md",
    "infra/bicep/main.bicep",
    "infra/bicep/modules/storage.bicep",
    "infra/bicep/modules/monitoring.bicep",
    "infra/bicep/modules/keyvault.bicep",
    "infra/bicep/modules/machine-learning.bicep",
    "infra/bicep/modules/data-factory.bicep",
    "infra/bicep/modules/purview.bicep",
    "infra/bicep/modules/ai-foundry.bicep",
    "infra/bicep/parameters/dev.example.json",
    "infra/bicep/parameters/test.example.json",
    "infra/bicep/parameters/prod.example.json",
    "infra/terraform/README.md",
    "infra/terraform/main.tf",
    "infra/terraform/variables.tf",
    "infra/terraform/outputs.tf",
    "infra/terraform/examples/dev.tfvars.example",
)
REQUIRED_SERVICES = {
    "Azure Event Hubs",
    "Azure Data Factory",
    "Azure Functions",
    "Azure Data Lake Storage Gen2",
    "Azure Machine Learning",
    "Azure AI Foundry",
    "Azure OpenAI",
    "Azure Monitor",
    "Log Analytics",
    "Application Insights",
    "Azure Data Explorer",
    "Microsoft Purview",
    "Microsoft Entra ID",
    "Azure Key Vault",
    "Microsoft Power BI",
    "Microsoft Fabric Lakehouse",
}
REQUIRED_DATA_ZONES = {"raw", "interim", "processed", "analytics_outputs", "reporting", "dashboard"}
REQUIRED_LOCAL_PATHS = {"data/raw", "data/interim", "data/processed", "outputs", "reports", "dashboard/outputs"}
KNOWN_SERVICES = REQUIRED_SERVICES | {"Azure AI Content Safety", "Azure Private Link", "Azure Virtual Network"}
SAFE_DISCLAIMER_TERMS = ("reference only", "non-deploying", "no azure resources are provisioned")


def validate(root: Path = REPO_ROOT) -> list[str]:
    """Return static Azure architecture validation failures."""
    failures: list[str] = []
    config = _load_config(root / "configs/azure_mapping.yaml", failures)
    if config:
        _validate_config(config, failures)
    _required_paths(root, REQUIRED_DOCS, "document", failures)
    _required_paths(root, REQUIRED_DIAGRAMS, "diagram", failures)
    _required_paths(root, REQUIRED_IAC, "infrastructure reference", failures)
    _validate_iac_disclaimers(root, failures)
    _validate_static_safety(root, failures)
    return failures


def main() -> int:
    """Run static architecture validation."""
    failures = validate()
    if failures:
        for failure in failures:
            print(f"Azure architecture validation failed: {failure}")
        return 1
    print("Azure architecture static validation passed.")
    return 0


def _load_config(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing Azure mapping config: {path.relative_to(REPO_ROOT)}")
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        failures.append("Azure mapping config root must be a mapping.")
        return {}
    return payload


def _validate_config(config: dict[str, Any], failures: list[str]) -> None:
    mapping = _section(config, "azure_mapping", failures)
    if mapping.get("deployment_mode") != "reference_only":
        failures.append("azure_mapping.deployment_mode must be reference_only.")
    if mapping.get("deployment_allowed") is not False:
        failures.append("azure_mapping.deployment_allowed must remain false.")
    environments = mapping.get("environments", [])
    if not isinstance(environments, list) or sorted(environments) != ["dev", "prod", "test"]:
        failures.append("environments must contain dev, test, and prod.")
    if len(environments) != len(set(environments)):
        failures.append("environments must not contain duplicates.")

    data_zones = _section(config, "data_zones", failures)
    if set(data_zones) != REQUIRED_DATA_ZONES:
        failures.append("data_zones must define raw, interim, processed, analytics_outputs, reporting, and dashboard.")
    local_paths = {zone.get("local_path") for zone in data_zones.values() if isinstance(zone, dict)}
    if local_paths != REQUIRED_LOCAL_PATHS:
        failures.append("data_zones local paths do not match implemented repository paths.")

    services = _flatten_services(_section(config, "services", failures))
    missing = sorted(REQUIRED_SERVICES - services)
    unknown = sorted(services - KNOWN_SERVICES)
    if missing:
        failures.append(f"missing required Azure services: {', '.join(missing)}")
    if unknown:
        failures.append(f"unknown Azure services: {', '.join(unknown)}")
    for section_name in ("security_controls", "governance_controls", "monitoring_mappings", "ml_mappings"):
        if not _section(config, section_name, failures):
            failures.append(f"{section_name} must not be empty.")
    policy = _section(config, "non_deployment_policy", failures)
    if policy.get("deployment_allowed") is not False or policy.get("ci_executes_iac") is not False:
        failures.append("non_deployment_policy must disable deployment and CI IaC execution.")
    _reject_secret_like_values(config, failures)


def _section(config: dict[str, Any], name: str, failures: list[str]) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        failures.append(f"{name} must be a mapping.")
        return {}
    return value


def _flatten_services(services: dict[str, Any]) -> set[str]:
    flattened: set[str] = set()
    for values in services.values():
        if isinstance(values, list):
            flattened.update(str(value) for value in values)
    return flattened


def _required_paths(root: Path, paths: tuple[str, ...], label: str, failures: list[str]) -> None:
    for relative in paths:
        if not (root / relative).is_file():
            failures.append(f"missing required {label}: {relative}")


def _validate_iac_disclaimers(root: Path, failures: list[str]) -> None:
    for relative in REQUIRED_IAC:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        if not all(term in text for term in SAFE_DISCLAIMER_TERMS):
            failures.append(f"infrastructure reference lacks non-deploying disclaimer: {relative}")


def _validate_static_safety(root: Path, failures: list[str]) -> None:
    files = [
        *root.glob(".github/workflows/*.yml"),
        root / "Makefile",
        *root.glob("infra/**/*"),
        *root.glob("docs/azure/*.md"),
        root / "configs/azure_mapping.yaml",
    ]
    forbidden_patterns = _forbidden_patterns()
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _guid_pattern().search(text):
            failures.append(f"real-looking tenant, subscription, or client ID found in {path.relative_to(root)}")
        for label, pattern in forbidden_patterns.items():
            if pattern.search(text):
                failures.append(f"forbidden deployment or credential pattern {label} found in {path.relative_to(root)}")
    for pattern in ("*.tfstate", "*.tfvars", "*.tfvars.json", ".env", "*.pem", "*.key"):
        for path in root.rglob(pattern):
            if path.name.endswith(".example"):
                continue
            failures.append(f"unsafe infrastructure or secret-like file present: {path.relative_to(root)}")


def _forbidden_patterns() -> dict[str, re.Pattern[str]]:
    commands = {
        "az-deployment-group": ("az", "deployment", "group", "create"),
        "az-deployment-sub": ("az", "deployment", "sub", "create"),
        "tf-apply": ("terraform", "apply"),
        "tf-plan": ("terraform", "plan"),
        "az-login": ("az", "login"),
        "arm-client-secret": ("ARM", "CLIENT", "SECRET"),
        "azure-client-secret": ("AZURE", "CLIENT", "SECRET"),
        "default-azure-credential": ("Default", "Azure", "Credential"),
    }
    return {
        label: re.compile(r"\b" + r"\s+".join(re.escape(part) for part in parts) + r"\b", re.IGNORECASE)
        for label, parts in commands.items()
    }


def _reject_secret_like_values(value: Any, failures: list[str]) -> None:
    text = json.dumps(value, sort_keys=True)
    patterns = {
        "guid": _guid_pattern(),
        "secret": re.compile(
            r"(secret|password|connectionstring|accountkey)\s*[:=]\s*['\"]?[A-Za-z0-9+/=]{12,}",
            re.IGNORECASE,
        ),
        "endpoint": re.compile(r"https://[A-Za-z0-9.-]+\.(vault|blob|dfs|openai|azure)\.", re.IGNORECASE),
    }
    for label, pattern in patterns.items():
        if pattern.search(text):
            failures.append(f"real-looking {label} value found in Azure mapping config.")


def _guid_pattern() -> re.Pattern[str]:
    return re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)


if __name__ == "__main__":
    raise SystemExit(main())
