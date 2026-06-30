"""Command-line tools for repository foundation validation."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence
from pathlib import Path

from airline_operations_intelligence.common.config import DEFAULT_CONFIG_PATH, load_platform_config
from airline_operations_intelligence.common.exceptions import (
    AirlineOperationsError,
    RepositoryValidationError,
)
from airline_operations_intelligence.common.logging import configure_logging, get_logger

LOGGER = get_logger(__name__)

REQUIRED_DIRECTORIES = (
    ".github/workflows",
    "configs",
    "dashboard",
    "data/raw",
    "data/interim",
    "data/processed",
    "diagrams",
    "docs/architecture",
    "docs/governance",
    "docs/operations",
    "docs/milestones",
    "outputs",
    "reports",
    "scripts",
    "src/airline_operations_intelligence",
    "tests/unit",
    "tests/integration",
    "tests/fixtures",
)

REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "pyproject.toml",
    "Makefile",
    ".github/workflows/quality.yml",
    "configs/platform.yaml",
)


def validate_repository(
    root: Path = Path("."),
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> list[str]:
    """Validate Milestone 1 repository foundation conditions."""
    root = root.resolve()
    failures: list[str] = []

    for directory in REQUIRED_DIRECTORIES:
        if not (root / directory).is_dir():
            failures.append(f"Missing required directory: {directory}")

    for file_path in REQUIRED_FILES:
        if not (root / file_path).is_file():
            failures.append(f"Missing required file: {file_path}")

    try:
        config = load_platform_config(root / config_path)
    except AirlineOperationsError as exc:
        failures.append(str(exc))
    else:
        for configured_path in config.paths.values():
            if not (root / configured_path).is_dir():
                failures.append(f"Configured path does not exist: {configured_path}")

    try:
        importlib.import_module("airline_operations_intelligence")
    except ImportError as exc:
        failures.append(f"Package import failed: {exc}")

    if failures:
        raise RepositoryValidationError("; ".join(failures))

    return ["Repository foundation validation passed."]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(prog="airline-ops-intel")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser(
        "validate-repository",
        help="Validate Milestone 1 repository structure, configuration, and package importability.",
    )
    validate_parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root to validate.",
    )
    validate_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to platform configuration, relative to the repository root unless absolute.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging()

    if args.command == "validate-repository":
        try:
            messages = validate_repository(root=args.root, config_path=args.config)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        for message in messages:
            LOGGER.info("%s", message)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
