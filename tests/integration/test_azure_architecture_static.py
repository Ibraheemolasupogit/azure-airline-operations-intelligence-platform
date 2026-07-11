from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_validate_azure_architecture_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_azure_architecture.py"],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Azure architecture static validation passed." in result.stdout


def test_makefile_and_workflow_include_static_validation_without_cloud_login() -> None:
    root = _repo_root()
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/quality.yml").read_text(encoding="utf-8")

    assert "validate-azure-architecture" in makefile
    assert "test-azure-architecture" in makefile
    assert "make validate-azure-architecture" in workflow
    assert "azure/login" not in workflow.lower()
    assert "ARM_CLIENT_SECRET" not in workflow
    assert "AZURE_CLIENT_SECRET" not in workflow


def test_no_azure_sdk_or_deployment_dependency_was_added() -> None:
    pyproject = (_repo_root() / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "azure-identity" not in pyproject
    assert "azure-mgmt" not in pyproject
    assert "azure-eventhub" not in pyproject
    assert "openai" not in pyproject


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
