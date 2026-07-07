"""End-to-end operational disruption scoring pipeline."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import DisruptionOutputCollisionError
from airline_operations_intelligence.data_generation.writers import sha256_file
from airline_operations_intelligence.disruption.alerts import generate_disruption_alerts
from airline_operations_intelligence.disruption.artefacts import (
    alert_payloads,
    write_features,
    write_json,
    write_jsonl,
    write_rows_csv,
    write_scores,
)
from airline_operations_intelligence.disruption.config import DisruptionScoringConfig, build_disruption_run_id
from airline_operations_intelligence.disruption.contracts import DisruptionRunResult, DisruptionSource
from airline_operations_intelligence.disruption.discovery import REQUIRED_PROCESSED, discover_disruption_source
from airline_operations_intelligence.disruption.features import build_disruption_features
from airline_operations_intelligence.disruption.lineage import build_lineage
from airline_operations_intelligence.disruption.reporting import (
    build_evidence_report,
    build_governance_report,
    build_summary,
)
from airline_operations_intelligence.disruption.scoring import score_disruption_rows
from airline_operations_intelligence.disruption.summaries import (
    aircraft_summary,
    airport_summary,
    component_summary,
    daily_summary,
    disruption_metrics,
    distribution,
    route_summary,
)


def score_disruptions(
    *,
    validation_report_dir: Path,
    config: DisruptionScoringConfig,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    disruption_run_id: str | None = None,
) -> DisruptionRunResult:
    """Run local governed disruption scoring."""
    source = discover_disruption_source(
        report_dir=validation_report_dir,
        config=config,
        passenger_forecast_report_dir=passenger_forecast_report_dir,
        delay_prediction_report_dir=delay_prediction_report_dir,
        maintenance_report_dir=maintenance_report_dir,
    )
    optional_ids = (
        source.passenger_forecast.run_id if source.passenger_forecast else None,
        source.delay_prediction.run_id if source.delay_prediction else None,
        source.maintenance_analytics.run_id if source.maintenance_analytics else None,
    )
    resolved_run_id = build_disruption_run_id(
        config, source.validation_run_id, optional_ids, __version__, disruption_run_id
    )
    final_output = config.settings.output_root / resolved_run_id
    final_report = config.settings.report_root / resolved_run_id
    tmp_output = config.settings.output_root / f".{resolved_run_id}.tmp"
    tmp_report = config.settings.report_root / f".{resolved_run_id}.tmp"
    finals = (final_output, final_report)
    tmps = (tmp_output, tmp_report)
    if any(path.exists() for path in finals) and not config.settings.overwrite:
        raise DisruptionOutputCollisionError(
            f"Disruption scoring run already exists: {resolved_run_id}. Use --overwrite."
        )
    for tmp in tmps:
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        for tmp in tmps:
            tmp.mkdir(parents=True, exist_ok=True)
        features = build_disruption_features(source)
        scores, leakage_checks = score_disruption_rows(features, config)
        alerts = generate_disruption_alerts(resolved_run_id, features, scores, config.settings.maximum_alerts_per_run)
        route_rows = route_summary(resolved_run_id, scores, features)
        airport_rows = airport_summary(resolved_run_id, scores, features)
        aircraft_rows = aircraft_summary(resolved_run_id, scores)
        daily_rows = daily_summary(resolved_run_id, scores, alerts)
        metric_rows = disruption_metrics(resolved_run_id, scores, alerts)
        checksums = {
            "disruption_features.csv": write_features(
                tmp_output / "disruption_features.csv", resolved_run_id, features
            ),
            "disruption_scores.csv": write_scores(tmp_output / "disruption_scores.csv", resolved_run_id, scores),
            "disruption_alerts.jsonl": write_jsonl(tmp_output / "disruption_alerts.jsonl", alert_payloads(alerts)),
            "route_disruption_summary.csv": write_rows_csv(tmp_output / "route_disruption_summary.csv", route_rows),
            "airport_disruption_summary.csv": write_rows_csv(
                tmp_output / "airport_disruption_summary.csv", airport_rows
            ),
            "aircraft_disruption_summary.csv": write_rows_csv(
                tmp_output / "aircraft_disruption_summary.csv", aircraft_rows
            ),
            "daily_disruption_summary.csv": write_rows_csv(tmp_output / "daily_disruption_summary.csv", daily_rows),
            "disruption-metrics.csv": write_rows_csv(tmp_output / "disruption-metrics.csv", metric_rows),
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
            leakage_checks,
            checksums,
            final_output,
            final_report,
        )
        manifest_checksum = write_json(tmp_output / "disruption-scoring-manifest.json", manifest)
        lineage_checksum = write_json(
            tmp_report / "lineage.json",
            build_lineage(
                disruption_run_id=resolved_run_id,
                source=source,
                output_dir=final_output,
                report_dir=final_report,
                config_fingerprint=config.fingerprint(),
                timestamp_utc=completed,
                package_version=__version__,
            ),
        )
        summary_checksum = _write_text(tmp_report / "disruption-scoring-summary.md", build_summary(manifest))
        evidence_checksum = _write_text(tmp_report / "disruption-evidence-report.md", build_evidence_report(manifest))
        governance_checksum = _write_text(
            tmp_report / "disruption-governance-report.md", build_governance_report(manifest)
        )
        manifest["artefact_checksums"]["disruption-scoring-manifest.json"] = manifest_checksum
        manifest["artefact_checksums"]["lineage.json"] = lineage_checksum
        manifest["artefact_checksums"]["disruption-scoring-summary.md"] = summary_checksum
        manifest["artefact_checksums"]["disruption-evidence-report.md"] = evidence_checksum
        manifest["artefact_checksums"]["disruption-governance-report.md"] = governance_checksum
        write_json(tmp_report / "disruption-scoring-manifest.json", manifest)
        for final in finals:
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_report.replace(final_report)
        return DisruptionRunResult(
            disruption_run_id=resolved_run_id,
            source_validation_run_id=source.validation_run_id,
            output_dir=final_output,
            report_dir=final_report,
            manifest_path=final_report / "disruption-scoring-manifest.json",
            scores_path=final_output / "disruption_scores.csv",
            alerts_path=final_output / "disruption_alerts.jsonl",
            overall_status="passed",
            row_counts={"features": len(features), "scores": len(scores), "alerts": len(alerts)},
        )
    except Exception:
        for tmp in tmps:
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _manifest(
    run_id: str,
    source: DisruptionSource,
    config: DisruptionScoringConfig,
    started: str,
    completed: str,
    features: list[Any],
    scores: list[Any],
    alerts: list[Any],
    leakage_checks: list[str],
    checksums: dict[str, str],
    output_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    highest = sorted(scores, key=lambda score: (-score.disruption_severity_score, score.flight_id))[:5]
    optional_inputs = {
        "passenger_forecast": source.passenger_forecast is not None,
        "delay_prediction": source.delay_prediction is not None,
        "maintenance_analytics": source.maintenance_analytics is not None,
    }
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "disruption_run_id": run_id,
        "source_validation_run_id": source.validation_run_id,
        "source_validation_manifest_sha256": source.validation_manifest_sha256,
        "source_processed_checksums": source.processed_checksums,
        "optional_passenger_forecast_run_id": source.passenger_forecast.run_id if source.passenger_forecast else None,
        "optional_passenger_forecast_manifest_sha256": source.passenger_forecast.manifest_sha256
        if source.passenger_forecast
        else None,
        "optional_delay_prediction_run_id": source.delay_prediction.run_id if source.delay_prediction else None,
        "optional_delay_prediction_manifest_sha256": source.delay_prediction.manifest_sha256
        if source.delay_prediction
        else None,
        "optional_maintenance_run_id": source.maintenance_analytics.run_id if source.maintenance_analytics else None,
        "optional_maintenance_manifest_sha256": source.maintenance_analytics.manifest_sha256
        if source.maintenance_analytics
        else None,
        "disruption_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "package_version": __version__,
        "seed": config.settings.seed,
        "input_datasets": list(REQUIRED_PROCESSED),
        "optional_inputs_used": optional_inputs,
        "scoring_policy": "deterministic weighted component scoring with separate forward and retrospective scores",
        "component_weights": config.settings.component_weights,
        "timing_and_leakage_policy": "; ".join(leakage_checks),
        "risk_band_policy": config.effective_configuration()["risk_bands"],
        "recovery_priority_policy": config.effective_configuration()["recovery_priority"],
        "row_counts": {"features": len(features), "scores": len(scores), "alerts": len(alerts)},
        "alert_counts": distribution([score.recovery_priority for score in scores]),
        "risk_band_counts": distribution([score.disruption_risk_band for score in scores]),
        "recovery_priority_counts": distribution([score.recovery_priority for score in scores]),
        "component_score_summary": component_summary(scores),
        "highest_risk_flights": [
            {
                "flight_id": score.flight_id,
                "score": score.disruption_severity_score,
                "driver": score.primary_disruption_driver,
            }
            for score in highest
        ],
        "output_artefacts": sorted(checksums),
        "artefact_checksums": dict(sorted(checksums.items())),
        "output_dirs": {"outputs": output_dir.as_posix(), "reports": report_dir.as_posix()},
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed",
        "synthetic_data_declaration": "All disruption scoring inputs and outputs are synthetic.",
        "responsible_use_disclaimer": "Decision-support analytics only; not autonomous recovery or operations control.",
        "known_limitations": [
            "Synthetic local scoring only; no live operations, monitoring, dashboards, GenAI, or Azure deployment.",
            (
                "Forward risk and retrospective severity are documented separately because outcomes are "
                "historical synthetic data."
            ),
        ],
        "milestone_scope": "Milestone 7 operational disruption scoring only.",
    }


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return sha256_file(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
