from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


def test_portfolio_readiness_validator_passes_for_repository() -> None:
    validator = _validator_module()

    assert validator.validate(_repo_root()) == []


def test_required_final_docs_and_diagrams_exist() -> None:
    validator = _validator_module()
    root = _repo_root()

    for relative in (*validator.REQUIRED_FINAL_DOCS, *validator.REQUIRED_FINAL_DIAGRAMS):
        assert (root / relative).is_file(), relative


def test_validator_detects_missing_required_doc(tmp_path: Path) -> None:
    validator = _validator_module()
    root = _copy_required_tree(tmp_path)
    (root / "docs/portfolio/portfolio-evidence-pack.md").unlink()

    failures = validator.validate(root)

    assert any("portfolio-evidence-pack.md" in failure for failure in failures)


def test_validator_detects_generated_artefact(tmp_path: Path) -> None:
    validator = _validator_module()
    root = _copy_required_tree(tmp_path)
    generated = root / "data/raw/test-run"
    generated.mkdir(parents=True)
    (generated / "flight_schedule.csv").write_text("flight_id\nF1\n", encoding="utf-8")

    failures = validator.validate(root)

    assert any("generated runtime artefact present" in failure for failure in failures)


def test_validator_detects_forbidden_command_and_makefile_gap(tmp_path: Path) -> None:
    validator = _validator_module()
    root = _copy_required_tree(tmp_path)
    (root / "docs/portfolio/portfolio-evidence-pack.md").write_text("terraform apply\n", encoding="utf-8")
    makefile = root / "Makefile"
    makefile.write_text(
        makefile.read_text(encoding="utf-8").replace(" validate-portfolio-readiness", ""), encoding="utf-8"
    )

    failures = validator.validate(root)

    assert any("terraform-apply" in failure for failure in failures)
    assert any("quality target must include validate-portfolio-readiness" in failure for failure in failures)


def test_validator_checks_roadmap_and_readme_sections(tmp_path: Path) -> None:
    validator = _validator_module()
    root = _copy_required_tree(tmp_path)
    (root / "docs/milestones/roadmap.md").write_text("| 1 - Only milestone |\n", encoding="utf-8")
    (root / "README.md").write_text("# Short\n", encoding="utf-8")

    failures = validator.validate(root)

    assert any("roadmap missing milestone 12" in failure for failure in failures)
    assert any("README missing section" in failure for failure in failures)


def _copy_required_tree(tmp_path: Path) -> Path:
    root = _repo_root()
    copy = tmp_path / "repo"
    for relative in (
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "Makefile",
        ".gitignore",
        ".github/workflows/quality.yml",
        "docs",
        "diagrams",
        "reports/architecture",
        "infra",
    ):
        source = root / relative
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    for relative in (
        "data/raw",
        "data/interim",
        "data/processed",
        "outputs",
        "dashboard/outputs",
        "reports/validation",
        "reports/passenger_forecasting",
        "reports/delay_prediction",
        "reports/maintenance_analytics",
        "reports/disruption_scoring",
        "reports/monitoring",
        "reports/genai_assistant",
        "reports/dashboard_outputs",
    ):
        path = copy / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / ".gitkeep").write_text("", encoding="utf-8")
    return copy


def _validator_module():
    path = _repo_root() / "scripts/validate_portfolio_readiness.py"
    spec = importlib.util.spec_from_file_location("validate_portfolio_readiness", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
