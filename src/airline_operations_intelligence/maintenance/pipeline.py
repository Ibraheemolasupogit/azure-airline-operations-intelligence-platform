"""End-to-end aircraft-health maintenance analytics pipeline."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import MaintenanceOutputCollisionError
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.maintenance.alerts import generate_alerts
from airline_operations_intelligence.maintenance.artefacts import (
    alert_payloads,
    write_features,
    write_json,
    write_jsonl,
    write_rows_csv,
    write_scores,
)
from airline_operations_intelligence.maintenance.config import (
    MaintenanceAnalyticsConfig,
    build_maintenance_run_id,
)
from airline_operations_intelligence.maintenance.contracts import MaintenanceRunResult, MaintenanceSource
from airline_operations_intelligence.maintenance.discovery import REQUIRED_PROCESSED, discover_maintenance_source
from airline_operations_intelligence.maintenance.evaluation import (
    aircraft_summary,
    component_summary,
    distribution,
    flight_risk,
    maintenance_metrics,
)
from airline_operations_intelligence.maintenance.features import build_health_features
from airline_operations_intelligence.maintenance.lineage import build_lineage
from airline_operations_intelligence.maintenance.reporting import (
    build_aircraft_health_report,
    build_governance_report,
    build_summary,
)
from airline_operations_intelligence.maintenance.scoring import score_health_rows


def analyse_aircraft_health(
    *,
    validation_report_dir: Path,
    config: MaintenanceAnalyticsConfig,
    maintenance_run_id: str | None = None,
) -> MaintenanceRunResult:
    """Run local governed maintenance analytics."""
    source = discover_maintenance_source(validation_report_dir, config)
    resolved_run_id = build_maintenance_run_id(config, source.validation_run_id, __version__, maintenance_run_id)
    final_output = config.settings.output_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    finals = (final_output, final_report)
    tmps = (tmp_output, tmp_report)
    if any(path.exists() for path in finals) and not config.settings.overwrite:
        raise MaintenanceOutputCollisionError(
            f"Maintenance analytics run already exists: {resolved_run_id}. Use --overwrite."
        )
    for tmp in tmps:
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        for tmp in tmps:
            tmp.mkdir(parents=True, exist_ok=True)
        features = build_health_features(source, config)
        scores = score_health_rows(features, config)
        alerts = generate_alerts(resolved_run_id, features, scores, config.settings.maximum_alerts_per_aircraft)
        aircraft_rows = aircraft_summary(resolved_run_id, scores)
        flight_rows = flight_risk(resolved_run_id, features, scores) if config.settings.enable_flight_level_risk else []
        metric_rows = maintenance_metrics(resolved_run_id, features, scores, alerts)
        checksums = {
            "aircraft_health_features.csv": write_features(
                tmp_output / "aircraft_health_features.csv", resolved_run_id, features
            ),
            "aircraft_health_scores.csv": write_scores(
                tmp_output / "aircraft_health_scores.csv", resolved_run_id, scores
            ),
            "maintenance_alerts.jsonl": write_jsonl(tmp_output / "maintenance_alerts.jsonl", alert_payloads(alerts)),
            "aircraft_health_summary.csv": write_rows_csv(tmp_output / "aircraft_health_summary.csv", aircraft_rows),
            "flight_maintenance_risk.csv": write_rows_csv(tmp_output / "flight_maintenance_risk.csv", flight_rows),
            "maintenance-metrics.csv": write_rows_csv(tmp_output / "maintenance-metrics.csv", metric_rows),
        }
        completed = _utc_now()
        manifest = _manifest(
            resolved_run_id,
            source,
            config,
            started,
            completed,
            features,
            scores,
            alerts,
            checksums,
            final_output,
            final_report,
        )
        manifest_checksum = write_json(tmp_output / "maintenance-analytics-manifest.json", manifest)
        lineage_checksum = write_json(
            tmp_report / "lineage.json",
            build_lineage(
                maintenance_run_id=resolved_run_id,
                source=source,
                output_dir=final_output,
                report_dir=final_report,
                config_fingerprint=config.fingerprint(),
                timestamp_utc=completed,
                package_version=__version__,
            ),
        )
        summary_checksum = _write_text(tmp_report / "maintenance-analytics-summary.md", build_summary(manifest))
        health_report_checksum = _write_text(
            tmp_report / "aircraft-health-report.md", build_aircraft_health_report(manifest)
        )
        governance_checksum = _write_text(
            tmp_report / "maintenance-governance-report.md", build_governance_report(manifest)
        )
        manifest["artefact_checksums"]["maintenance-analytics-manifest.json"] = manifest_checksum
        manifest["artefact_checksums"]["lineage.json"] = lineage_checksum
        manifest["artefact_checksums"]["maintenance-analytics-summary.md"] = summary_checksum
        manifest["artefact_checksums"]["aircraft-health-report.md"] = health_report_checksum
        manifest["artefact_checksums"]["maintenance-governance-report.md"] = governance_checksum
        write_json(tmp_report / "maintenance-analytics-manifest.json", manifest)
        for final in finals:
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_report.replace(final_report)
        return MaintenanceRunResult(
            maintenance_run_id=resolved_run_id,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            report_dir=final_report,
            manifest_path=final_report / "maintenance-analytics-manifest.json",
            scores_path=final_output / "aircraft_health_scores.csv",
            alerts_path=final_output / "maintenance_alerts.jsonl",
            overall_status="passed",
            row_counts={
                "features": len(features),
                "scores": len(scores),
                "alerts": len(alerts),
                "aircraft_summary": len(aircraft_rows),
                "flight_risk": len(flight_rows),
            },
        )
    except Exception:
        for tmp in tmps:
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _manifest(
    run_id: str,
    source: MaintenanceSource,
    config: MaintenanceAnalyticsConfig,
    started: str,
    completed: str,
    features: list[Any],
    scores: list[Any],
    alerts: list[Any],
    checksums: dict[str, str],
    output_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    risk_band_counts = distribution([score.risk_band for score in scores])
    alert_counts = distribution([score.alert_category for score in scores])
    highest = max(scores, key=lambda score: (score.maintenance_risk_score, score.aircraft_id))
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "maintenance_run_id": run_id,
        "source_validation_run_id": source.validation_run_id,
        "source_validation_manifest_sha256": source.validation_manifest_sha256,
        "source_processed_checksums": source.processed_checksums,
        "maintenance_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "package_version": __version__,
        "seed": config.settings.seed,
        "input_datasets": list(REQUIRED_PROCESSED),
        "telemetry_bounds_policy": config.effective_configuration()["telemetry_bounds"],
        "scoring_policy": "deterministic rules, robust anomaly scores, trends, utilisation, fault-code evidence",
        "alert_policy": config.settings.alert_thresholds,
        "score_weighting": config.settings.risk_weights,
        "row_counts": {
            "features": len(features),
            "scores": len(scores),
            "alerts": len(alerts),
        },
        "aircraft_count": len({row.aircraft_id for row in features}),
        "linked_flight_count": len({row.flight_id for row in features if row.flight_id}),
        "alert_counts": alert_counts,
        "risk_band_counts": risk_band_counts,
        "component_score_summary": component_summary(scores),
        "highest_risk_aircraft": highest.aircraft_id,
        "output_artefacts": sorted(checksums),
        "artefact_checksums": dict(sorted(checksums.items())),
        "output_dirs": {"outputs": output_dir.as_posix(), "reports": report_dir.as_posix()},
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed",
        "synthetic_data_declaration": "All maintenance analytics inputs and outputs are synthetic.",
        "aviation_safety_disclaimer": (
            "Not certified predictive maintenance, airworthiness evidence, or safety-critical diagnostics."
        ),
        "human_review_required": True,
        "known_limitations": [
            "Rules and statistical scores are synthetic decision-support evidence only.",
            (
                "No Azure services, live telemetry, dashboards, monitoring, "
                "or maintenance-control actions are implemented."
            ),
        ],
        "milestone_scope": "Milestone 6 aircraft-health and maintenance analytics only.",
    }


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
