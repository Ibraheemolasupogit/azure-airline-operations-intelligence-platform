"""Command-line tools for repository validation and synthetic data generation."""

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
from airline_operations_intelligence.data_generation.config import (
    DEFAULT_GENERATION_CONFIG_PATH,
    load_generation_config,
    with_overrides,
)
from airline_operations_intelligence.data_generation.manifest import describe_manifest
from airline_operations_intelligence.data_generation.orchestrator import generate_data

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
    "configs/data_generation.yaml",
    "configs/data_generation_ci.yaml",
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

    generate_parser = subparsers.add_parser(
        "generate-data",
        help="Generate deterministic synthetic aviation datasets for Milestone 2.",
    )
    generate_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_GENERATION_CONFIG_PATH,
        help="Generation YAML configuration path.",
    )
    generate_parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Explicit filesystem-safe run ID. Defaults to a deterministic config-derived value.",
    )
    generate_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Override the configured output root. Must remain under data/raw.",
    )
    generate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the configured deterministic seed.",
    )
    generate_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing run directory with the same run ID.",
    )

    describe_parser = subparsers.add_parser(
        "describe-generation",
        help="Describe a completed synthetic data-generation run from its manifest.",
    )
    describe_parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Completed generation run directory containing generation-manifest.json.",
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

    if args.command == "generate-data":
        try:
            config = load_generation_config(args.config)
            config = with_overrides(
                config,
                seed=args.seed,
                output_root=args.output_root,
                overwrite=True if args.overwrite else None,
            )
            result = generate_data(config, run_id=args.run_id)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info("Generated synthetic aviation data run %s at %s", result.run_id, result.run_dir)
        for filename, row_count in result.row_counts.items():
            LOGGER.info("%s: %s rows", filename, row_count)
        return 0

    if args.command == "describe-generation":
        try:
            description = describe_manifest(args.run_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
