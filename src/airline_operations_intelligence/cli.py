"""Command-line tools for repository, generation, and validation workflows."""

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
from airline_operations_intelligence.dashboard.config import (
    DEFAULT_DASHBOARD_CONFIG_PATH,
    load_dashboard_config,
)
from airline_operations_intelligence.dashboard.config import (
    with_overrides as with_dashboard_overrides,
)
from airline_operations_intelligence.dashboard.pipeline import build_dashboard_outputs
from airline_operations_intelligence.dashboard.reporting import describe_dashboard_report
from airline_operations_intelligence.data_generation.config import (
    DEFAULT_GENERATION_CONFIG_PATH,
    load_generation_config,
    with_overrides,
)
from airline_operations_intelligence.data_generation.manifest import describe_manifest
from airline_operations_intelligence.data_generation.orchestrator import generate_data
from airline_operations_intelligence.delay_prediction.config import (
    DEFAULT_DELAY_PREDICTION_CONFIG_PATH,
    load_delay_prediction_config,
)
from airline_operations_intelligence.delay_prediction.config import (
    with_overrides as with_delay_prediction_overrides,
)
from airline_operations_intelligence.delay_prediction.pipeline import predict_flight_delays
from airline_operations_intelligence.delay_prediction.reporting import describe_delay_prediction_report
from airline_operations_intelligence.disruption.config import (
    DEFAULT_DISRUPTION_SCORING_CONFIG_PATH,
    load_disruption_config,
)
from airline_operations_intelligence.disruption.config import (
    with_overrides as with_disruption_overrides,
)
from airline_operations_intelligence.disruption.pipeline import score_disruptions
from airline_operations_intelligence.disruption.reporting import describe_disruption_report
from airline_operations_intelligence.forecasting.config import (
    DEFAULT_FORECASTING_CONFIG_PATH,
    load_forecasting_config,
)
from airline_operations_intelligence.forecasting.config import (
    with_overrides as with_forecasting_overrides,
)
from airline_operations_intelligence.forecasting.pipeline import forecast_passenger_demand
from airline_operations_intelligence.forecasting.reporting import describe_forecast_report
from airline_operations_intelligence.genai.config import (
    DEFAULT_GENAI_ASSISTANT_CONFIG_PATH,
    load_genai_assistant_config,
)
from airline_operations_intelligence.genai.config import (
    with_overrides as with_genai_assistant_overrides,
)
from airline_operations_intelligence.genai.pipeline import run_operations_assistant
from airline_operations_intelligence.genai.reporting import describe_assistant_report
from airline_operations_intelligence.maintenance.config import (
    DEFAULT_MAINTENANCE_ANALYTICS_CONFIG_PATH,
    load_maintenance_config,
)
from airline_operations_intelligence.maintenance.config import (
    with_overrides as with_maintenance_overrides,
)
from airline_operations_intelligence.maintenance.pipeline import analyse_aircraft_health
from airline_operations_intelligence.maintenance.reporting import describe_aircraft_health_report
from airline_operations_intelligence.monitoring.config import (
    DEFAULT_MONITORING_CONFIG_PATH,
    load_monitoring_config,
)
from airline_operations_intelligence.monitoring.config import (
    with_overrides as with_monitoring_overrides,
)
from airline_operations_intelligence.monitoring.pipeline import monitor_platform
from airline_operations_intelligence.monitoring.reporting import describe_monitoring_report
from airline_operations_intelligence.validation.config import (
    DEFAULT_VALIDATION_CONFIG_PATH,
    load_validation_config,
)
from airline_operations_intelligence.validation.config import (
    with_overrides as with_validation_overrides,
)
from airline_operations_intelligence.validation.pipeline import validate_data
from airline_operations_intelligence.validation.reporting import describe_validation_manifest

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
    "configs/validation.yaml",
    "configs/validation_ci.yaml",
    "configs/passenger_forecasting.yaml",
    "configs/passenger_forecasting_ci.yaml",
    "configs/delay_prediction.yaml",
    "configs/delay_prediction_ci.yaml",
    "configs/maintenance_analytics.yaml",
    "configs/maintenance_analytics_ci.yaml",
    "configs/disruption_scoring.yaml",
    "configs/disruption_scoring_ci.yaml",
    "configs/monitoring.yaml",
    "configs/monitoring_ci.yaml",
    "configs/genai_assistant.yaml",
    "configs/genai_assistant_ci.yaml",
    "configs/dashboard_outputs.yaml",
    "configs/dashboard_outputs_ci.yaml",
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

    validate_data_parser = subparsers.add_parser(
        "validate-data",
        help="Validate a completed Milestone 2 generation run into governed Milestone 3 outputs.",
    )
    validate_data_parser.add_argument(
        "--source-run-dir",
        type=Path,
        required=True,
        help="Completed source generation run directory under data/raw.",
    )
    validate_data_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_VALIDATION_CONFIG_PATH,
        help="Validation YAML configuration path.",
    )
    validate_data_parser.add_argument(
        "--validation-run-id",
        type=str,
        default=None,
        help="Explicit filesystem-safe validation run ID.",
    )
    validate_data_parser.add_argument(
        "--interim-root",
        type=Path,
        default=None,
        help="Override the configured interim output root. Must remain under data/interim.",
    )
    validate_data_parser.add_argument(
        "--processed-root",
        type=Path,
        default=None,
        help="Override the configured processed output root. Must remain under data/processed.",
    )
    validate_data_parser.add_argument(
        "--report-root",
        type=Path,
        default=None,
        help="Override the configured report root. Must remain under reports/validation.",
    )
    validate_data_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing validation outputs for the same validation run ID.",
    )
    validate_data_parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Fail the validation run when warnings exceed the configured threshold.",
    )
    validate_data_parser.add_argument(
        "--no-quarantine",
        action="store_true",
        help="Disable quarantine output writing.",
    )

    describe_validation_parser = subparsers.add_parser(
        "describe-validation",
        help="Describe a completed governed validation run from its validation manifest.",
    )
    describe_validation_parser.add_argument(
        "--report-dir",
        type=Path,
        required=True,
        help="Completed validation report directory containing validation-manifest.json.",
    )

    forecast_parser = subparsers.add_parser(
        "forecast-passenger-demand",
        help="Train and evaluate deterministic passenger-demand forecasts for Milestone 4.",
    )
    forecast_parser.add_argument(
        "--validation-report-dir",
        type=Path,
        required=True,
        help="Completed Milestone 3 validation report directory.",
    )
    forecast_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_FORECASTING_CONFIG_PATH,
        help="Passenger forecasting YAML configuration path.",
    )
    forecast_parser.add_argument(
        "--forecast-run-id",
        type=str,
        default=None,
        help="Explicit filesystem-safe forecast run ID.",
    )
    forecast_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Override forecast output root under outputs/passenger_forecasting.",
    )
    forecast_parser.add_argument(
        "--model-root",
        type=Path,
        default=None,
        help="Override model output root under outputs/models/passenger_forecasting.",
    )
    forecast_parser.add_argument(
        "--report-root",
        type=Path,
        default=None,
        help="Override report root under reports/passenger_forecasting.",
    )
    forecast_parser.add_argument("--seed", type=int, default=None, help="Override deterministic model seed.")
    forecast_parser.add_argument(
        "--prediction-horizon-days",
        type=int,
        default=None,
        help="Override configured booking horizon.",
    )
    forecast_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing forecast/model/report outputs for the same run ID.",
    )

    describe_forecast_parser = subparsers.add_parser(
        "describe-passenger-forecast",
        help="Describe a completed passenger forecasting run without retraining.",
    )
    describe_forecast_parser.add_argument(
        "--forecast-report-dir",
        type=Path,
        required=True,
        help="Completed passenger forecasting report directory containing forecast-manifest.json.",
    )

    delay_parser = subparsers.add_parser(
        "predict-flight-delays",
        help="Train and evaluate deterministic flight-delay prediction for Milestone 5.",
    )
    delay_parser.add_argument(
        "--validation-report-dir",
        type=Path,
        required=True,
        help="Completed Milestone 3 validation report directory.",
    )
    delay_parser.add_argument(
        "--passenger-forecast-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 4 forecast report directory.",
    )
    delay_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_DELAY_PREDICTION_CONFIG_PATH,
        help="Delay prediction YAML configuration path.",
    )
    delay_parser.add_argument(
        "--delay-run-id",
        type=str,
        default=None,
        help="Explicit filesystem-safe delay prediction run ID.",
    )
    delay_parser.add_argument("--output-root", type=Path, default=None, help="Override delay output root.")
    delay_parser.add_argument("--model-root", type=Path, default=None, help="Override delay model root.")
    delay_parser.add_argument("--report-root", type=Path, default=None, help="Override delay report root.")
    delay_parser.add_argument("--seed", type=int, default=None, help="Override deterministic model seed.")
    delay_parser.add_argument(
        "--delay-threshold-minutes",
        type=int,
        default=None,
        help="Override target delay threshold in minutes.",
    )
    delay_parser.add_argument(
        "--prediction-cutoff-minutes",
        type=int,
        default=None,
        help="Override pre-departure prediction cutoff in minutes.",
    )
    delay_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing delay prediction/model/report outputs for the same run ID.",
    )

    describe_delay_parser = subparsers.add_parser(
        "describe-delay-prediction",
        help="Describe a completed delay prediction run without retraining.",
    )
    describe_delay_parser.add_argument(
        "--delay-report-dir",
        type=Path,
        required=True,
        help="Completed delay prediction report directory containing delay-prediction-manifest.json.",
    )

    maintenance_parser = subparsers.add_parser(
        "analyse-aircraft-health",
        help="Run deterministic aircraft-health and maintenance analytics for Milestone 6.",
    )
    maintenance_parser.add_argument(
        "--validation-report-dir",
        type=Path,
        required=True,
        help="Completed Milestone 3 validation report directory.",
    )
    maintenance_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_MAINTENANCE_ANALYTICS_CONFIG_PATH,
        help="Maintenance analytics YAML configuration path.",
    )
    maintenance_parser.add_argument(
        "--maintenance-run-id",
        type=str,
        default=None,
        help="Explicit filesystem-safe maintenance analytics run ID.",
    )
    maintenance_parser.add_argument("--output-root", type=Path, default=None, help="Override maintenance output root.")
    maintenance_parser.add_argument("--report-root", type=Path, default=None, help="Override maintenance report root.")
    maintenance_parser.add_argument("--seed", type=int, default=None, help="Override deterministic seed.")
    maintenance_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing maintenance output/report directories for the same run ID.",
    )

    describe_maintenance_parser = subparsers.add_parser(
        "describe-aircraft-health",
        help="Describe a completed aircraft-health analytics run without rerunning analytics.",
    )
    describe_maintenance_parser.add_argument(
        "--maintenance-report-dir",
        type=Path,
        required=True,
        help="Completed maintenance analytics report directory containing maintenance-analytics-manifest.json.",
    )

    disruption_parser = subparsers.add_parser(
        "score-disruptions",
        help="Score operational disruption severity and recovery priority for Milestone 7.",
    )
    disruption_parser.add_argument(
        "--validation-report-dir",
        type=Path,
        required=True,
        help="Completed Milestone 3 validation report directory.",
    )
    disruption_parser.add_argument(
        "--passenger-forecast-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 4 passenger forecast report directory.",
    )
    disruption_parser.add_argument(
        "--delay-prediction-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 5 delay prediction report directory.",
    )
    disruption_parser.add_argument(
        "--maintenance-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 6 maintenance analytics report directory.",
    )
    disruption_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_DISRUPTION_SCORING_CONFIG_PATH,
        help="Disruption scoring YAML configuration path.",
    )
    disruption_parser.add_argument("--disruption-run-id", type=str, default=None, help="Explicit disruption run ID.")
    disruption_parser.add_argument("--output-root", type=Path, default=None, help="Override disruption output root.")
    disruption_parser.add_argument("--report-root", type=Path, default=None, help="Override disruption report root.")
    disruption_parser.add_argument("--seed", type=int, default=None, help="Override deterministic seed.")
    disruption_parser.add_argument("--overwrite", action="store_true", help="Replace existing disruption outputs.")

    describe_disruption_parser = subparsers.add_parser(
        "describe-disruption-scoring",
        help="Describe a completed disruption scoring run without rerunning scoring.",
    )
    describe_disruption_parser.add_argument(
        "--disruption-report-dir",
        type=Path,
        required=True,
        help="Completed disruption scoring report directory containing disruption-scoring-manifest.json.",
    )

    monitoring_parser = subparsers.add_parser(
        "monitor-platform",
        help="Create local monitoring and observability evidence for Milestone 8.",
    )
    monitoring_parser.add_argument(
        "--generation-run-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 2 generation run directory.",
    )
    monitoring_parser.add_argument(
        "--validation-report-dir",
        type=Path,
        required=True,
        help="Completed Milestone 3 validation report directory.",
    )
    monitoring_parser.add_argument(
        "--passenger-forecast-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 4 passenger forecast report directory.",
    )
    monitoring_parser.add_argument(
        "--delay-prediction-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 5 delay prediction report directory.",
    )
    monitoring_parser.add_argument(
        "--maintenance-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 6 maintenance analytics report directory.",
    )
    monitoring_parser.add_argument(
        "--disruption-report-dir",
        type=Path,
        default=None,
        help="Optional completed Milestone 7 disruption scoring report directory.",
    )
    monitoring_parser.add_argument(
        "--baseline-monitoring-report-dir",
        type=Path,
        default=None,
        help="Optional previous monitoring report directory for deterministic drift comparison.",
    )
    monitoring_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_MONITORING_CONFIG_PATH,
        help="Monitoring YAML configuration path.",
    )
    monitoring_parser.add_argument("--monitoring-run-id", type=str, default=None, help="Explicit monitoring run ID.")
    monitoring_parser.add_argument("--output-root", type=Path, default=None, help="Override monitoring output root.")
    monitoring_parser.add_argument("--report-root", type=Path, default=None, help="Override monitoring report root.")
    monitoring_parser.add_argument("--seed", type=int, default=None, help="Override deterministic seed.")
    monitoring_parser.add_argument("--overwrite", action="store_true", help="Replace existing monitoring outputs.")

    describe_monitoring_parser = subparsers.add_parser(
        "describe-monitoring",
        help="Describe a completed monitoring run without rerunning checks.",
    )
    describe_monitoring_parser.add_argument(
        "--monitoring-report-dir",
        type=Path,
        required=True,
        help="Completed monitoring report directory containing monitoring-manifest.json.",
    )

    assistant_parser = subparsers.add_parser(
        "run-operations-assistant",
        help="Run the deterministic local GenAI-style operations assistant for Milestone 9.",
    )
    assistant_parser.add_argument("--generation-run-dir", type=Path, default=None)
    assistant_parser.add_argument("--validation-report-dir", type=Path, required=True)
    assistant_parser.add_argument("--passenger-forecast-report-dir", type=Path, default=None)
    assistant_parser.add_argument("--delay-prediction-report-dir", type=Path, default=None)
    assistant_parser.add_argument("--maintenance-report-dir", type=Path, default=None)
    assistant_parser.add_argument("--disruption-report-dir", type=Path, default=None)
    assistant_parser.add_argument("--monitoring-report-dir", type=Path, default=None)
    assistant_parser.add_argument("--config", type=Path, default=DEFAULT_GENAI_ASSISTANT_CONFIG_PATH)
    assistant_parser.add_argument("--intent", type=str, required=True)
    assistant_parser.add_argument("--flight-id", type=str, default=None)
    assistant_parser.add_argument("--route-id", type=str, default=None)
    assistant_parser.add_argument("--aircraft-id", type=str, default=None)
    assistant_parser.add_argument("--airport-code", type=str, default=None)
    assistant_parser.add_argument("--assistant-run-id", type=str, default=None)
    assistant_parser.add_argument("--output-root", type=Path, default=None)
    assistant_parser.add_argument("--report-root", type=Path, default=None)
    assistant_parser.add_argument("--seed", type=int, default=None)
    assistant_parser.add_argument("--overwrite", action="store_true")

    describe_assistant_parser = subparsers.add_parser(
        "describe-operations-assistant",
        help="Describe a completed operations assistant run without rerunning.",
    )
    describe_assistant_parser.add_argument(
        "--assistant-report-dir",
        type=Path,
        required=True,
        help="Completed assistant report directory containing assistant-run-manifest.json.",
    )

    dashboard_parser = subparsers.add_parser(
        "build-dashboard-outputs",
        help="Build local Power BI-ready dashboard outputs for Milestone 10.",
    )
    dashboard_parser.add_argument("--generation-run-dir", type=Path, default=None)
    dashboard_parser.add_argument("--validation-report-dir", type=Path, required=True)
    dashboard_parser.add_argument("--passenger-forecast-report-dir", type=Path, default=None)
    dashboard_parser.add_argument("--delay-prediction-report-dir", type=Path, default=None)
    dashboard_parser.add_argument("--maintenance-report-dir", type=Path, default=None)
    dashboard_parser.add_argument("--disruption-report-dir", type=Path, required=True)
    dashboard_parser.add_argument("--monitoring-report-dir", type=Path, required=True)
    dashboard_parser.add_argument("--assistant-report-dir", type=Path, default=None)
    dashboard_parser.add_argument("--config", type=Path, default=DEFAULT_DASHBOARD_CONFIG_PATH)
    dashboard_parser.add_argument("--dashboard-run-id", type=str, default=None)
    dashboard_parser.add_argument("--output-root", type=Path, default=None)
    dashboard_parser.add_argument("--report-root", type=Path, default=None)
    dashboard_parser.add_argument("--seed", type=int, default=None)
    dashboard_parser.add_argument("--overwrite", action="store_true")

    describe_dashboard_parser = subparsers.add_parser(
        "describe-dashboard-outputs",
        help="Describe completed dashboard outputs without rebuilding.",
    )
    describe_dashboard_parser.add_argument(
        "--dashboard-report-dir",
        type=Path,
        required=True,
        help="Completed dashboard report directory containing dashboard-output-manifest.json.",
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
            generation_config = load_generation_config(args.config)
            generation_config = with_overrides(
                generation_config,
                seed=args.seed,
                output_root=args.output_root,
                overwrite=True if args.overwrite else None,
            )
            generation_result = generate_data(generation_config, run_id=args.run_id)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Generated synthetic aviation data run %s at %s",
            generation_result.run_id,
            generation_result.run_dir,
        )
        for filename, row_count in generation_result.row_counts.items():
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

    if args.command == "validate-data":
        try:
            validation_config = load_validation_config(args.config)
            validation_config = with_validation_overrides(
                validation_config,
                interim_root=args.interim_root,
                processed_root=args.processed_root,
                report_root=args.report_root,
                overwrite=True if args.overwrite else None,
                fail_on_warning=True if args.fail_on_warning else None,
                quarantine_invalid_records=False if args.no_quarantine else None,
            )
            validation_result = validate_data(
                source_run_dir=args.source_run_dir,
                config=validation_config,
                validation_run_id=args.validation_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Validated source run %s as %s",
            validation_result.source_run_id,
            validation_result.validation_run_id,
        )
        LOGGER.info("Overall status: %s", validation_result.overall_status)
        for filename, counts in validation_result.row_counts.items():
            LOGGER.info(
                "%s: source=%s valid=%s quarantined=%s",
                filename,
                counts["source"],
                counts["valid"],
                counts["quarantined"],
            )
        return 0 if validation_result.overall_status == "passed" else 1

    if args.command == "describe-validation":
        try:
            description = describe_validation_manifest(args.report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "forecast-passenger-demand":
        try:
            forecasting_config = load_forecasting_config(args.config)
            forecasting_config = with_forecasting_overrides(
                forecasting_config,
                output_root=args.output_root,
                model_root=args.model_root,
                report_root=args.report_root,
                seed=args.seed,
                prediction_horizon_days=args.prediction_horizon_days,
                overwrite=True if args.overwrite else None,
            )
            forecast_result = forecast_passenger_demand(
                validation_report_dir=args.validation_report_dir,
                config=forecasting_config,
                forecast_run_id=args.forecast_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Forecasted passenger demand for validation run %s as %s",
            forecast_result.source_validation_run_id,
            forecast_result.forecast_run_id,
        )
        LOGGER.info("Champion model: %s", forecast_result.champion_model_id)
        LOGGER.info("Partition rows: %s", forecast_result.partition_row_counts)
        return 0 if forecast_result.overall_status == "passed" else 1

    if args.command == "describe-passenger-forecast":
        try:
            description = describe_forecast_report(args.forecast_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "predict-flight-delays":
        try:
            delay_config = load_delay_prediction_config(args.config)
            delay_config = with_delay_prediction_overrides(
                delay_config,
                output_root=args.output_root,
                model_root=args.model_root,
                report_root=args.report_root,
                seed=args.seed,
                delay_threshold_minutes=args.delay_threshold_minutes,
                prediction_cutoff_minutes=args.prediction_cutoff_minutes,
                overwrite=True if args.overwrite else None,
            )
            delay_result = predict_flight_delays(
                validation_report_dir=args.validation_report_dir,
                passenger_forecast_report_dir=args.passenger_forecast_report_dir,
                config=delay_config,
                delay_run_id=args.delay_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Predicted flight delays for validation run %s as %s",
            delay_result.source_validation_run_id,
            delay_result.delay_run_id,
        )
        LOGGER.info("Champion model: %s", delay_result.champion_model_id)
        LOGGER.info("Selected probability threshold: %.3f", delay_result.selected_threshold)
        LOGGER.info("Partition rows: %s", delay_result.partition_row_counts)
        return 0 if delay_result.overall_status == "passed" else 1

    if args.command == "describe-delay-prediction":
        try:
            description = describe_delay_prediction_report(args.delay_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "analyse-aircraft-health":
        try:
            maintenance_config = load_maintenance_config(args.config)
            maintenance_config = with_maintenance_overrides(
                maintenance_config,
                output_root=args.output_root,
                report_root=args.report_root,
                seed=args.seed,
                overwrite=True if args.overwrite else None,
            )
            maintenance_result = analyse_aircraft_health(
                validation_report_dir=args.validation_report_dir,
                config=maintenance_config,
                maintenance_run_id=args.maintenance_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Analysed aircraft health for validation run %s as %s",
            maintenance_result.source_validation_run_id,
            maintenance_result.maintenance_run_id,
        )
        LOGGER.info("Row counts: %s", maintenance_result.row_counts)
        return 0 if maintenance_result.overall_status == "passed" else 1

    if args.command == "describe-aircraft-health":
        try:
            description = describe_aircraft_health_report(args.maintenance_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "score-disruptions":
        try:
            disruption_config = load_disruption_config(args.config)
            disruption_config = with_disruption_overrides(
                disruption_config,
                output_root=args.output_root,
                report_root=args.report_root,
                seed=args.seed,
                overwrite=True if args.overwrite else None,
            )
            disruption_result = score_disruptions(
                validation_report_dir=args.validation_report_dir,
                passenger_forecast_report_dir=args.passenger_forecast_report_dir,
                delay_prediction_report_dir=args.delay_prediction_report_dir,
                maintenance_report_dir=args.maintenance_report_dir,
                config=disruption_config,
                disruption_run_id=args.disruption_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Scored disruptions for validation run %s as %s",
            disruption_result.source_validation_run_id,
            disruption_result.disruption_run_id,
        )
        LOGGER.info("Row counts: %s", disruption_result.row_counts)
        return 0 if disruption_result.overall_status == "passed" else 1

    if args.command == "describe-disruption-scoring":
        try:
            description = describe_disruption_report(args.disruption_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "monitor-platform":
        try:
            monitoring_config = load_monitoring_config(args.config)
            monitoring_config = with_monitoring_overrides(
                monitoring_config,
                output_root=args.output_root,
                report_root=args.report_root,
                seed=args.seed,
                overwrite=True if args.overwrite else None,
            )
            monitoring_result = monitor_platform(
                generation_run_dir=args.generation_run_dir,
                validation_report_dir=args.validation_report_dir,
                passenger_forecast_report_dir=args.passenger_forecast_report_dir,
                delay_prediction_report_dir=args.delay_prediction_report_dir,
                maintenance_report_dir=args.maintenance_report_dir,
                disruption_report_dir=args.disruption_report_dir,
                baseline_monitoring_report_dir=args.baseline_monitoring_report_dir,
                config=monitoring_config,
                monitoring_run_id=args.monitoring_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Monitored platform validation run %s as %s",
            monitoring_result.source_validation_run_id,
            monitoring_result.monitoring_run_id,
        )
        LOGGER.info("Row counts: %s", monitoring_result.row_counts)
        return 0 if monitoring_result.overall_status == "passed" else 1

    if args.command == "describe-monitoring":
        try:
            description = describe_monitoring_report(args.monitoring_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "run-operations-assistant":
        try:
            assistant_config = load_genai_assistant_config(args.config)
            assistant_config = with_genai_assistant_overrides(
                assistant_config,
                output_root=args.output_root,
                report_root=args.report_root,
                seed=args.seed,
                overwrite=True if args.overwrite else None,
            )
            assistant_result = run_operations_assistant(
                generation_run_dir=args.generation_run_dir,
                validation_report_dir=args.validation_report_dir,
                passenger_forecast_report_dir=args.passenger_forecast_report_dir,
                delay_prediction_report_dir=args.delay_prediction_report_dir,
                maintenance_report_dir=args.maintenance_report_dir,
                disruption_report_dir=args.disruption_report_dir,
                monitoring_report_dir=args.monitoring_report_dir,
                config=assistant_config,
                intent=args.intent,
                flight_id=args.flight_id,
                route_id=args.route_id,
                aircraft_id=args.aircraft_id,
                airport_code=args.airport_code,
                assistant_run_id=args.assistant_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Ran operations assistant for validation run %s as %s",
            assistant_result.source_validation_run_id,
            assistant_result.assistant_run_id,
        )
        LOGGER.info("Row counts: %s", assistant_result.row_counts)
        return 0 if assistant_result.overall_status == "passed" else 1

    if args.command == "describe-operations-assistant":
        try:
            description = describe_assistant_report(args.assistant_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    if args.command == "build-dashboard-outputs":
        try:
            dashboard_config = load_dashboard_config(args.config)
            dashboard_config = with_dashboard_overrides(
                dashboard_config,
                output_root=args.output_root,
                report_root=args.report_root,
                seed=args.seed,
                overwrite=True if args.overwrite else None,
            )
            dashboard_result = build_dashboard_outputs(
                generation_run_dir=args.generation_run_dir,
                validation_report_dir=args.validation_report_dir,
                passenger_forecast_report_dir=args.passenger_forecast_report_dir,
                delay_prediction_report_dir=args.delay_prediction_report_dir,
                maintenance_report_dir=args.maintenance_report_dir,
                disruption_report_dir=args.disruption_report_dir,
                monitoring_report_dir=args.monitoring_report_dir,
                assistant_report_dir=args.assistant_report_dir,
                config=dashboard_config,
                dashboard_run_id=args.dashboard_run_id,
            )
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        LOGGER.info(
            "Built dashboard outputs for validation run %s as %s",
            dashboard_result.source_validation_run_id,
            dashboard_result.dashboard_run_id,
        )
        LOGGER.info("Row counts: %s", dashboard_result.row_counts)
        return 0 if dashboard_result.overall_status == "passed" else 1

    if args.command == "describe-dashboard-outputs":
        try:
            description = describe_dashboard_report(args.dashboard_report_dir)
        except AirlineOperationsError as exc:
            LOGGER.error("%s", exc)
            return 1
        print(description)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
