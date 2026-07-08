"""End-to-end local platform monitoring pipeline."""

from __future__ import annotations

import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import MonitoringOutputCollisionError
from airline_operations_intelligence.monitoring.alerts import generate_monitoring_alerts
from airline_operations_intelligence.monitoring.artefacts import (
    dataclass_rows,
    write_csv_rows,
    write_json,
    write_jsonl,
    write_text,
)
from airline_operations_intelligence.monitoring.checks import run_monitoring_checks
from airline_operations_intelligence.monitoring.config import MonitoringConfig, build_monitoring_run_id
from airline_operations_intelligence.monitoring.contracts import MonitoringRunResult
from airline_operations_intelligence.monitoring.discovery import discover_monitoring_source
from airline_operations_intelligence.monitoring.drift import compare_drift
from airline_operations_intelligence.monitoring.lineage import build_lineage
from airline_operations_intelligence.monitoring.metrics import extract_metrics
from airline_operations_intelligence.monitoring.reporting import (
    build_governance_report,
    build_platform_health_report,
    build_summary,
)
from airline_operations_intelligence.monitoring.summaries import domain_health_summary, platform_health_summary


def monitor_platform(
    *,
    validation_report_dir: Path,
    config: MonitoringConfig,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    disruption_report_dir: Path | None = None,
    baseline_monitoring_report_dir: Path | None = None,
    monitoring_run_id: str | None = None,
) -> MonitoringRunResult:
    """Run local monitoring over explicit platform artefacts."""
    source = discover_monitoring_source(
        validation_report_dir=validation_report_dir,
        config=config,
        generation_run_dir=generation_run_dir,
        passenger_forecast_report_dir=passenger_forecast_report_dir,
        delay_prediction_report_dir=delay_prediction_report_dir,
        maintenance_report_dir=maintenance_report_dir,
        disruption_report_dir=disruption_report_dir,
        baseline_monitoring_report_dir=baseline_monitoring_report_dir,
    )
    optional_ids = (
        _optional_id(source.optional_manifests.get("passenger_forecasting"), "forecast_run_id"),
        _optional_id(source.optional_manifests.get("delay_prediction"), "delay_run_id"),
        _optional_id(source.optional_manifests.get("maintenance_analytics"), "maintenance_run_id"),
        _optional_id(source.optional_manifests.get("disruption_scoring"), "disruption_run_id"),
    )
    baseline_id = source.baseline_manifest.get("monitoring_run_id") if source.baseline_manifest else None
    resolved_run_id = build_monitoring_run_id(
        config, source.validation_run_id, optional_ids, baseline_id, __version__, monitoring_run_id
    )
    final_output = config.settings.output_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    if any(path.exists() for path in (final_output, final_report)) and not config.settings.overwrite:
        raise MonitoringOutputCollisionError(f"Monitoring run already exists: {resolved_run_id}. Use --overwrite.")
    for tmp in (tmp_output, tmp_report):
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        tmp_output.mkdir(parents=True, exist_ok=True)
        tmp_report.mkdir(parents=True, exist_ok=True)
        timestamp = _stable_timestamp(config.settings.seed)
        metrics = extract_metrics(source)
        checks = run_monitoring_checks(source, metrics, config, timestamp)
        drift = compare_drift(metrics, source.baseline_manifest, config)
        alerts = generate_monitoring_alerts(resolved_run_id, checks, config)
        source_run_ids, source_manifest_paths = _source_maps(source)
        domain_rows = domain_health_summary(
            resolved_run_id, metrics, checks, alerts, source_run_ids, source_manifest_paths
        )
        platform_rows = platform_health_summary(resolved_run_id, domain_rows, checks, alerts, timestamp)
        checksums = _write_outputs(
            resolved_run_id, tmp_output, metrics, checks, alerts, domain_rows, platform_rows, drift
        )
        manifest = _manifest(
            resolved_run_id,
            source,
            config,
            started,
            _utc_now(),
            metrics,
            checks,
            drift,
            alerts,
            domain_rows,
            platform_rows,
            checksums,
            final_output,
            final_report,
        )
        write_json(tmp_output / "monitoring-manifest.json", manifest)
        lineage = build_lineage(
            monitoring_run_id=resolved_run_id,
            source=source,
            output_dir=final_output,
            report_dir=final_report,
            config_fingerprint=config.fingerprint(),
            checks_executed=[check.rule_id for check in checks],
            metrics_produced=[metric.metric_name for metric in metrics],
            alerts_produced=len(alerts),
            artefact_checksums=checksums,
            timestamp_utc=manifest["completed_at_utc"],
            package_version=__version__,
        )
        checksums["lineage.json"] = write_json(tmp_report / "lineage.json", lineage)
        checksums["monitoring-summary.md"] = write_text(tmp_report / "monitoring-summary.md", build_summary(manifest))
        checksums["platform-health-report.md"] = write_text(
            tmp_report / "platform-health-report.md", build_platform_health_report(manifest)
        )
        checksums["monitoring-governance-report.md"] = write_text(
            tmp_report / "monitoring-governance-report.md", build_governance_report(manifest)
        )
        manifest["artefact_checksums"] = dict(sorted(checksums.items()))
        manifest["output_artefacts"] = sorted(checksums)
        write_json(tmp_output / "monitoring-manifest.json", manifest)
        write_json(tmp_report / "monitoring-manifest.json", manifest)
        for final in (final_output, final_report):
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_report.replace(final_report)
        return MonitoringRunResult(
            monitoring_run_id=resolved_run_id,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            report_dir=final_report,
            manifest_path=final_report / "monitoring-manifest.json",
            overall_status=manifest["overall_status"],
            row_counts=manifest["row_counts"],
        )
    except Exception:
        for tmp in (tmp_output, tmp_report):
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _write_outputs(
    run_id: str,
    output_dir: Path,
    metrics: list[Any],
    checks: list[Any],
    alerts: list[Any],
    domain_rows: list[dict[str, object]],
    platform_rows: list[dict[str, object]],
    drift: list[Any],
) -> dict[str, str]:
    checksums: dict[str, str] = {}
    checksums["monitoring-metrics.csv"] = write_csv_rows(
        output_dir / "monitoring-metrics.csv",
        dataclass_rows(metrics, monitoring_run_id=run_id),
        [
            "monitoring_run_id",
            "monitoring_domain",
            "metric_name",
            "metric_value",
            "numerator",
            "denominator",
            "status",
            "severity",
            "threshold",
            "source_run_id",
            "evidence_path",
            "notes",
        ],
    )
    checksums["monitoring-checks.jsonl"] = write_jsonl(
        output_dir / "monitoring-checks.jsonl", dataclass_rows(checks, monitoring_run_id=run_id)
    )
    checksums["monitoring-alerts.jsonl"] = write_jsonl(
        output_dir / "monitoring-alerts.jsonl", dataclass_rows(alerts, monitoring_run_id=run_id)
    )
    checksums["domain-health-summary.csv"] = write_csv_rows(
        output_dir / "domain-health-summary.csv",
        domain_rows,
        [
            "monitoring_run_id",
            "monitoring_domain",
            "domain_status",
            "highest_severity",
            "metric_count",
            "check_count",
            "passed_check_count",
            "warning_check_count",
            "failed_check_count",
            "skipped_check_count",
            "alert_count",
            "source_run_id",
            "source_manifest_path",
        ],
    )
    checksums["platform-health-summary.csv"] = write_csv_rows(
        output_dir / "platform-health-summary.csv",
        platform_rows,
        [
            "monitoring_run_id",
            "overall_health_status",
            "highest_severity",
            "domain_count",
            "monitored_domain_count",
            "passed_check_count",
            "warning_check_count",
            "failed_check_count",
            "skipped_check_count",
            "alert_count",
            "critical_alert_count",
            "high_alert_count",
            "generated_at_utc",
        ],
    )
    checksums["drift-comparison.csv"] = write_csv_rows(
        output_dir / "drift-comparison.csv",
        dataclass_rows(drift, monitoring_run_id=run_id),
        [
            "monitoring_run_id",
            "monitoring_domain",
            "metric_name",
            "current_value",
            "baseline_value",
            "absolute_change",
            "relative_change",
            "threshold",
            "status",
            "severity",
            "notes",
        ],
    )
    return checksums


def _manifest(
    run_id: str,
    source: Any,
    config: MonitoringConfig,
    started: str,
    completed: str,
    metrics: list[Any],
    checks: list[Any],
    drift: list[Any],
    alerts: list[Any],
    domain_rows: list[dict[str, object]],
    platform_rows: list[dict[str, object]],
    checksums: dict[str, str],
    output_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    check_counts = _status_counts(checks)
    alert_counts = _severity_counts(alerts)
    platform = platform_rows[0]
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "monitoring_run_id": run_id,
        "source_generation_run_id": source.generation_run_id,
        "source_validation_run_id": source.validation_run_id,
        "optional_passenger_forecast_run_id": _optional_id(
            source.optional_manifests.get("passenger_forecasting"), "forecast_run_id"
        ),
        "optional_delay_prediction_run_id": _optional_id(
            source.optional_manifests.get("delay_prediction"), "delay_run_id"
        ),
        "optional_maintenance_run_id": _optional_id(
            source.optional_manifests.get("maintenance_analytics"), "maintenance_run_id"
        ),
        "optional_disruption_run_id": _optional_id(
            source.optional_manifests.get("disruption_scoring"), "disruption_run_id"
        ),
        "baseline_monitoring_run_id": source.baseline_manifest.get("monitoring_run_id")
        if source.baseline_manifest
        else None,
        "monitoring_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "package_version": __version__,
        "seed": config.settings.seed,
        "monitored_domains": sorted({metric.monitoring_domain for metric in metrics}),
        "accepted_inputs": [
            asdict(item)
            | {
                "path": item.path.as_posix(),
                "manifest_path": item.manifest_path.as_posix() if item.manifest_path else None,
            }
            for item in source.accepted_inputs
        ],
        "rejected_inputs": [
            asdict(item)
            | {
                "path": item.path.as_posix(),
                "manifest_path": item.manifest_path.as_posix() if item.manifest_path else None,
            }
            for item in source.rejected_inputs
        ],
        "input_manifest_checksums": source.input_manifest_checksums,
        "input_artefact_checksums_verified": source.input_artefact_checksums_verified,
        "monitoring_policy": {
            "accepted_statuses": list(config.settings.accepted_statuses),
            "severity_policy": config.settings.severity_policy,
            "alert_limit": config.settings.maximum_alerts_per_run,
        },
        "drift_policy": {
            "enabled": config.settings.enable_drift_checks,
            "status": "compared" if source.baseline_manifest else "skipped",
            "warning_threshold": config.settings.thresholds["drift_relative_change_warning"],
        },
        "row_counts": {
            "metrics": len(metrics),
            "checks": len(checks),
            "alerts": len(alerts),
            "domains": len(domain_rows),
            "drift": len(drift),
        },
        "metric_counts": _domain_counts(metrics, "monitoring_domain"),
        "check_counts": check_counts,
        "alert_counts": alert_counts,
        "highest_severity": platform["highest_severity"],
        "overall_health_status": platform["overall_health_status"],
        "output_artefacts": sorted(checksums),
        "artefact_checksums": dict(sorted(checksums.items())),
        "output_dirs": {"outputs": output_dir.as_posix(), "reports": report_dir.as_posix()},
        "domain_health": domain_rows,
        "platform_health": platform_rows,
        "metric_values": [asdict(metric) for metric in metrics],
        "check_summary": [asdict(check) for check in checks],
        "drift_summary": [asdict(row) for row in drift],
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed" if check_counts["failed"] == 0 else "failed",
        "synthetic_data_declaration": "Monitoring evidence is generated from fictional synthetic aviation data only.",
        "responsible_use_disclaimer": (
            "Local portfolio monitoring evidence only; not live operations or safety-critical alerting."
        ),
        "known_limitations": [
            "No Azure Monitor, Application Insights, Log Analytics, or alert routing clients are implemented.",
            (
                "Drift-style comparison is deterministic relative change evidence, not statistically validated "
                "production drift."
            ),
            "Synthetic metric behaviour may contain unrealistic correlations and requires human review.",
        ],
        "milestone_scope": "Milestone 8 monitoring and observability only.",
    }


def _status_counts(rows: list[Any]) -> dict[str, int]:
    return {
        status: sum(1 for row in rows if row.status == status) for status in ("passed", "warning", "failed", "skipped")
    }


def _severity_counts(rows: list[Any]) -> dict[str, int]:
    counts = {
        severity: sum(1 for row in rows if row.severity == severity)
        for severity in ("info", "warning", "high", "critical")
    }
    counts["total"] = len(rows)
    return counts


def _domain_counts(rows: list[Any], attr: str) -> dict[str, int]:
    domains = sorted({getattr(row, attr) for row in rows})
    return {domain: sum(1 for row in rows if getattr(row, attr) == domain) for domain in domains}


def _source_maps(source: Any) -> tuple[dict[str, str | None], dict[str, str | None]]:
    ids = {
        "generation": source.generation_run_id,
        "validation": source.validation_run_id,
        "passenger_forecasting": _optional_id(
            source.optional_manifests.get("passenger_forecasting"), "forecast_run_id"
        ),
        "delay_prediction": _optional_id(source.optional_manifests.get("delay_prediction"), "delay_run_id"),
        "maintenance_analytics": _optional_id(
            source.optional_manifests.get("maintenance_analytics"), "maintenance_run_id"
        ),
        "disruption_scoring": _optional_id(source.optional_manifests.get("disruption_scoring"), "disruption_run_id"),
    }
    paths = {
        "generation": source.generation_manifest_path.as_posix() if source.generation_manifest_path else None,
        "validation": source.validation_manifest_path.as_posix(),
    }
    paths.update(
        {
            domain: (report_dir / _manifest_name(domain)).as_posix()
            for domain, report_dir in source.optional_report_dirs.items()
        }
    )
    return ids, paths


def _manifest_name(domain: str) -> str:
    return {
        "passenger_forecasting": "forecast-manifest.json",
        "delay_prediction": "delay-prediction-manifest.json",
        "maintenance_analytics": "maintenance-analytics-manifest.json",
        "disruption_scoring": "disruption-scoring-manifest.json",
    }[domain]


def _optional_id(manifest: dict[str, Any] | None, key: str) -> str | None:
    return str(manifest[key]) if manifest and manifest.get(key) is not None else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _stable_timestamp(seed: int) -> str:
    day = seed % 28 + 1
    return f"2025-01-{day:02d}T00:00:00Z"
