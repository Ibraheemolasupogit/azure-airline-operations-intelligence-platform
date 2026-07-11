"""Static validation for Milestone 12 portfolio readiness."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FINAL_DOCS = (
    "docs/portfolio/portfolio-evidence-pack.md",
    "docs/portfolio/milestone-evidence-index.md",
    "docs/portfolio/interviewer-guide.md",
    "docs/portfolio/capability-matrix.md",
    "docs/architecture/final-platform-architecture.md",
    "docs/operations/final-local-validation.md",
    "reports/architecture/final-repository-health.md",
    "docs/milestones/milestone-12.md",
)
REQUIRED_FINAL_DIAGRAMS = (
    "diagrams/final-platform-flow.mmd",
    "diagrams/final-azure-target-flow.mmd",
    "diagrams/final-evidence-lineage.mmd",
)
README_REQUIRED_SECTIONS = (
    "Business Scenario",
    "Architecture Overview",
    "Implemented Capabilities By Milestone",
    "Azure Service Mapping",
    "Repository Structure",
    "Quick Start",
    "Local Validation",
    "Key CLI Examples",
    "Quality Gate",
    "Generated Artefact Policy",
    "Evidence And Documentation Map",
    "Responsible Use",
    "Limitations",
    "Future Work",
)
REQUIRED_MAKE_TARGETS = (
    "lint",
    "typecheck",
    "test",
    "docs-check",
    "yaml-check",
    "validate",
    "validate-azure-architecture",
    "validate-portfolio-readiness",
    "quality",
    "clean",
)
GENERATED_PATHS = (
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
)
ALLOWED_PLACEHOLDERS = {".gitkeep"}
FORBIDDEN_FILES = (".env", "terraform.tfstate", "terraform.tfvars")
FORBIDDEN_COMMANDS = {
    "az-login": ("az", "login"),
    "az-deployment-group": ("az", "deployment", "group", "create"),
    "az-deployment-sub": ("az", "deployment", "sub", "create"),
    "terraform-apply": ("terraform", "apply"),
    "terraform-destroy": ("terraform", "destroy"),
    "openai-sdk-import": ("from", "openai", "import"),
    "azure-sdk-credential": ("Default", "Azure", "Credential"),
}
GITIGNORE_REQUIRED_PATTERNS = (
    "data/raw/*",
    "data/interim/*",
    "data/processed/*",
    "outputs/*",
    "dashboard/outputs/*",
    "reports/validation/*",
    "reports/dashboard_outputs/*",
    ".env",
    "*.tfstate",
)


def validate(root: Path = REPO_ROOT) -> list[str]:
    """Return portfolio readiness validation failures."""
    failures: list[str] = []
    _required_paths(root, REQUIRED_FINAL_DOCS, "final document", failures)
    _required_paths(root, REQUIRED_FINAL_DIAGRAMS, "final diagram", failures)
    _validate_readme(root / "README.md", failures)
    _validate_roadmap(root / "docs/milestones/roadmap.md", failures)
    _validate_generated_paths(root, failures)
    _validate_secret_like_files(root, failures)
    _validate_forbidden_commands(root, failures)
    _validate_makefile(root / "Makefile", failures)
    _validate_ci(root / ".github/workflows/quality.yml", failures)
    _validate_gitignore(root / ".gitignore", failures)
    return failures


def main() -> int:
    """Run static portfolio readiness validation."""
    failures = validate()
    if failures:
        for failure in failures:
            print(f"Portfolio readiness validation failed: {failure}")
        return 1
    print("Portfolio readiness static validation passed.")
    return 0


def _required_paths(root: Path, paths: tuple[str, ...], label: str, failures: list[str]) -> None:
    for relative in paths:
        if not (root / relative).is_file():
            failures.append(f"missing required {label}: {relative}")


def _validate_readme(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append("missing README.md")
        return
    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    for section in README_REQUIRED_SECTIONS:
        if f"## {section.lower()}" not in lower:
            failures.append(f"README missing section: {section}")
    for phrase in (
        "no azure resources are provisioned",
        "synthetic",
        "local-first",
        "target-state",
        "not a certified aviation",
    ):
        if phrase not in lower:
            failures.append(f"README missing boundary phrase: {phrase}")


def _validate_roadmap(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append("missing roadmap")
        return
    text = path.read_text(encoding="utf-8")
    for milestone in range(1, 13):
        if f"| {milestone} -" not in text:
            failures.append(f"roadmap missing milestone {milestone}")


def _validate_generated_paths(root: Path, failures: list[str]) -> None:
    for relative in GENERATED_PATHS:
        path = root / relative
        if not path.exists():
            continue
        for child in path.rglob("*"):
            if child.name in ALLOWED_PLACEHOLDERS:
                continue
            if child.is_dir() and not any(
                grandchild.is_file() and grandchild.name not in ALLOWED_PLACEHOLDERS for grandchild in child.rglob("*")
            ):
                continue
            failures.append(f"generated runtime artefact present: {child.relative_to(root)}")


def _validate_secret_like_files(root: Path, failures: list[str]) -> None:
    for name in FORBIDDEN_FILES:
        for path in root.rglob(name):
            if ".git" in path.parts:
                continue
            if path.name == ".env.example":
                continue
            failures.append(f"secret or environment-specific file present: {path.relative_to(root)}")


def _validate_forbidden_commands(root: Path, failures: list[str]) -> None:
    patterns = _forbidden_command_patterns()
    for path in _scannable_files(root):
        text = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(text):
                failures.append(f"forbidden live integration or deployment command {label} in {path.relative_to(root)}")
        if _guid_pattern().search(text):
            failures.append(f"real-looking GUID found in {path.relative_to(root)}")


def _validate_makefile(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append("missing Makefile")
        return
    text = path.read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if not re.search(rf"^{re.escape(target)}:", text, re.MULTILINE):
            failures.append(f"Makefile missing target: {target}")
    if "validate-portfolio-readiness" not in _make_target_body(text, "quality"):
        failures.append("quality target must include validate-portfolio-readiness")


def _validate_ci(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append("missing quality workflow")
        return
    text = path.read_text(encoding="utf-8")
    if "make validate-portfolio-readiness" not in text:
        failures.append("quality workflow must run portfolio readiness validation")
    for forbidden in ("azure/login", "az login", "terraform apply", "terraform destroy"):
        if forbidden in text.lower():
            failures.append(f"quality workflow contains forbidden deployment step: {forbidden}")


def _validate_gitignore(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append("missing .gitignore")
        return
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    for pattern in GITIGNORE_REQUIRED_PATTERNS:
        if pattern not in lines:
            failures.append(f".gitignore missing generated artefact protection: {pattern}")


def _forbidden_command_patterns() -> dict[str, re.Pattern[str]]:
    return {
        label: re.compile(r"\b" + r"\s+".join(re.escape(part) for part in parts) + r"\b", re.IGNORECASE)
        for label, parts in FORBIDDEN_COMMANDS.items()
    }


def _guid_pattern() -> re.Pattern[str]:
    return re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)


def _scannable_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in ("README.md", "CONTRIBUTING.md", "SECURITY.md", "Makefile", "docs/**/*.md", "infra/**/*.md"):
        paths.extend(path for path in root.glob(pattern) if path.is_file())
    return paths


def _make_target_body(text: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:(?P<body>.*?)(?=^[A-Za-z0-9_.-]+:|\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    return match.group("body") if match else ""


if __name__ == "__main__":
    raise SystemExit(main())
