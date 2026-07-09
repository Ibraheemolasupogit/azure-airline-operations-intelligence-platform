"""End-to-end local dashboard-output pipeline."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from airline_operations_intelligence import __version__
from airline_operations_intelligence.common.exceptions import DashboardOutputCollisionError
from airline_operations_intelligence.dashboard.artefacts import write_csv_rows, write_json, write_text
from airline_operations_intelligence.dashboard.config import DashboardConfig, build_dashboard_run_id
from airline_operations_intelligence.dashboard.contracts import DashboardRunResult
from airline_operations_intelligence.dashboard.data_dictionary import build_data_dictionary, dictionary_markdown
from airline_operations_intelligence.dashboard.dimensions import build_dimensions
from airline_operations_intelligence.dashboard.discovery import discover_dashboard_source
from airline_operations_intelligence.dashboard.facts import build_facts
from airline_operations_intelligence.dashboard.lineage import build_lineage
from airline_operations_intelligence.dashboard.measures import build_kpis, build_summaries, measure_catalogue
from airline_operations_intelligence.dashboard.page_specs import build_page_specs
from airline_operations_intelligence.dashboard.quality import run_quality_checks
from airline_operations_intelligence.dashboard.readers import load_source_tables
from airline_operations_intelligence.dashboard.reporting import (
    build_governance_report,
    build_semantic_report,
    build_summary,
    measures_markdown,
    pages_markdown,
)
from airline_operations_intelligence.dashboard.semantic_model import build_semantic_model


def build_dashboard_outputs(
    *,
    validation_report_dir: Path,
    disruption_report_dir: Path,
    monitoring_report_dir: Path,
    config: DashboardConfig,
    generation_run_dir: Path | None = None,
    passenger_forecast_report_dir: Path | None = None,
    delay_prediction_report_dir: Path | None = None,
    maintenance_report_dir: Path | None = None,
    assistant_report_dir: Path | None = None,
    dashboard_run_id: str | None = None,
) -> DashboardRunResult:
    """Build local Power BI-ready dashboard outputs from explicit artefacts."""
    source = discover_dashboard_source(
        validation_report_dir=validation_report_dir,
        disruption_report_dir=disruption_report_dir,
        monitoring_report_dir=monitoring_report_dir,
        generation_run_dir=generation_run_dir,
        passenger_forecast_report_dir=passenger_forecast_report_dir,
        delay_prediction_report_dir=delay_prediction_report_dir,
        maintenance_report_dir=maintenance_report_dir,
        assistant_report_dir=assistant_report_dir,
        config=config,
    )
    optional_ids = tuple(artefact.run_id for _, artefact in sorted(source.optional.items()))
    run_id = build_dashboard_run_id(
        config,
        source.validation.run_id,
        source.disruption.run_id,
        source.monitoring.run_id,
        optional_ids,
        __version__,
        dashboard_run_id,
    )
    final_output = config.settings.output_root / run_id
    final_report = config.settings.report_root / run_id
    tmp_output = config.settings.output_root / f".{run_id}.tmp"
    tmp_report = config.settings.report_root / f".{run_id}.tmp"
    if any(path.exists() for path in (final_output, final_report)) and not config.settings.overwrite:
        raise DashboardOutputCollisionError(f"Dashboard run already exists: {run_id}. Use --overwrite.")
    for tmp in (tmp_output, tmp_report):
        if tmp.exists():
            shutil.rmtree(tmp)
    started = _utc_now()
    try:
        tmp_output.mkdir(parents=True, exist_ok=True)
        tmp_report.mkdir(parents=True, exist_ok=True)
        source_tables = load_source_tables(source)
        source_run_ids = _source_run_ids(source)
        dimensions = build_dimensions(run_id, source_tables, config)
        facts = build_facts(run_id, source_tables, source_run_ids)
        kpis = build_kpis(run_id, facts, config)
        summaries = build_summaries(run_id, facts)
        tables = {**dimensions, **facts, **kpis, **summaries}
        measures = measure_catalogue()
        semantic_model = build_semantic_model(tables, measures, config)
        pages = build_page_specs()
        dictionary_rows = build_data_dictionary(tables)
        quality_rows, quality_summary = run_quality_checks(tables, semantic_model, measures, pages, dictionary_rows)
        checksums = _write_outputs(tmp_output, tables, semantic_model, measures, pages, dictionary_rows, quality_rows)
        manifest = _manifest(
            run_id=run_id,
            source=source,
            config=config,
            started=started,
            completed=_utc_now(),
            tables=tables,
            measures=measures,
            pages=pages,
            quality_summary=quality_summary,
            checksums=checksums,
            final_output=final_output,
            final_report=final_report,
        )
        write_json(tmp_output / "dashboard-output-manifest.json", manifest)
        lineage = build_lineage(source, run_id, checksums)
        checksums["lineage.json"] = write_json(tmp_report / "lineage.json", lineage)
        checksums["dashboard-output-summary.md"] = write_text(
            tmp_report / "dashboard-output-summary.md", build_summary(manifest)
        )
        checksums["semantic-model-report.md"] = write_text(
            tmp_report / "semantic-model-report.md", build_semantic_report(manifest)
        )
        checksums["dashboard-governance-report.md"] = write_text(
            tmp_report / "dashboard-governance-report.md", build_governance_report(manifest)
        )
        checksums["dashboard-data-dictionary.md"] = write_text(
            tmp_report / "dashboard-data-dictionary.md", dictionary_markdown(dictionary_rows)
        )
        checksums["dashboard-page-specs.md"] = write_text(tmp_report / "dashboard-page-specs.md", pages_markdown(pages))
        manifest["artefact_checksums"] = dict(sorted(checksums.items()))
        manifest["output_artefacts"] = sorted([*checksums, "dashboard-output-manifest.json"])
        write_json(tmp_output / "dashboard-output-manifest.json", manifest)
        write_json(tmp_report / "dashboard-output-manifest.json", manifest)
        for final in (final_output, final_report):
            if final.exists():
                shutil.rmtree(final)
        tmp_output.replace(final_output)
        tmp_report.replace(final_report)
        return DashboardRunResult(
            dashboard_run_id=run_id,
            source_validation_run_id=source.validation.run_id,
            source_disruption_run_id=source.disruption.run_id,
            source_monitoring_run_id=source.monitoring.run_id,
            output_dir=final_output,
            report_dir=final_report,
            manifest_path=final_report / "dashboard-output-manifest.json",
            overall_status="passed",
            row_counts={table: len(rows) for table, rows in tables.items()},
        )
    except Exception:
        for tmp in (tmp_output, tmp_report):
            if tmp.exists():
                shutil.rmtree(tmp)
        raise


def _write_outputs(
    output_dir: Path,
    tables: dict[str, list[dict[str, object]]],
    semantic_model: dict[str, Any],
    measures: list[dict[str, str]],
    pages: list[dict[str, object]],
    dictionary_rows: list[dict[str, object]],
    quality_rows: list[dict[str, object]],
) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for table_name, rows in sorted(tables.items()):
        checksums[f"{table_name}.csv"] = write_csv_rows(
            output_dir / f"{table_name}.csv", rows, _fieldnames(table_name, rows)
        )
    checksums["powerbi-semantic-model.json"] = write_json(output_dir / "powerbi-semantic-model.json", semantic_model)
    checksums["measure-catalogue.json"] = write_json(output_dir / "measure-catalogue.json", measures)
    checksums["measure-catalogue.md"] = write_text(output_dir / "measure-catalogue.md", measures_markdown(measures))
    checksums["dashboard-page-specs.json"] = write_json(output_dir / "dashboard-page-specs.json", pages)
    checksums["dashboard-data-dictionary.json"] = write_json(
        output_dir / "dashboard-data-dictionary.json", dictionary_rows
    )
    checksums["dashboard-quality-results.json"] = write_json(
        output_dir / "dashboard-quality-results.json", {"checks": quality_rows}
    )
    checksums["dashboard-quality-metrics.csv"] = write_csv_rows(
        output_dir / "dashboard-quality-metrics.csv",
        quality_rows,
        ["rule_id", "status", "observed_value", "message"],
    )
    return checksums


def _manifest(
    *,
    run_id: str,
    source: Any,
    config: DashboardConfig,
    started: str,
    completed: str,
    tables: dict[str, list[dict[str, object]]],
    measures: list[dict[str, str]],
    pages: list[dict[str, object]],
    quality_summary: dict[str, object],
    checksums: dict[str, str],
    final_output: Path,
    final_report: Path,
) -> dict[str, Any]:
    optional = source.optional
    return {
        "schema_version": "1.0",
        "project_name": "azure-airline-operations-intelligence-platform",
        "dashboard_run_id": run_id,
        "source_validation_run_id": source.validation.run_id,
        "source_disruption_run_id": source.disruption.run_id,
        "source_monitoring_run_id": source.monitoring.run_id,
        "optional_generation_run_id": source.validation.manifest.get("source_generation_run_id")
        if source.generation_run_dir
        else None,
        "optional_passenger_forecast_run_id": optional.get("passenger_forecasting").run_id
        if "passenger_forecasting" in optional
        else None,
        "optional_delay_prediction_run_id": optional.get("delay_prediction").run_id
        if "delay_prediction" in optional
        else None,
        "optional_maintenance_run_id": optional.get("maintenance_analytics").run_id
        if "maintenance_analytics" in optional
        else None,
        "optional_assistant_run_id": optional.get("genai_assistant").run_id if "genai_assistant" in optional else None,
        "dashboard_configuration": config.effective_configuration(),
        "configuration_fingerprint": config.fingerprint(),
        "package_version": __version__,
        "seed": config.settings.seed,
        "input_manifest_checksums": {
            "validation": source.validation.manifest_sha256,
            "disruption_scoring": source.disruption.manifest_sha256,
            "monitoring": source.monitoring.manifest_sha256,
            **{domain: artefact.manifest_sha256 for domain, artefact in optional.items()},
        },
        "input_artefact_checksums_verified": {
            "validation": True,
            "disruption_scoring": source.disruption.artefact_checksums_verified,
            "monitoring": source.monitoring.artefact_checksums_verified,
            **{domain: artefact.artefact_checksums_verified for domain, artefact in optional.items()},
        },
        "tables_created": sorted(tables),
        "skipped_optional_tables": [
            table
            for table in (
                "fact_passenger_forecast",
                "fact_delay_prediction",
                "fact_maintenance_risk",
                "fact_assistant_response",
            )
            if len(tables.get(table, [])) == 0
        ],
        "row_counts": {table: len(rows) for table, rows in sorted(tables.items())},
        "kpi_counts": {table: len(rows) for table, rows in sorted(tables.items()) if table.startswith("kpi_")},
        "semantic_model_summary": {"table_count": len(tables), "relationship_count": len(_relationships(tables))},
        "measure_count": len(measures),
        "page_spec_count": len(pages),
        "quality_check_summary": quality_summary,
        "output_artefacts": sorted(checksums),
        "artefact_checksums": dict(sorted(checksums.items())),
        "output_dirs": {"outputs": final_output.as_posix(), "reports": final_report.as_posix()},
        "started_at_utc": started,
        "completed_at_utc": completed,
        "overall_status": "passed",
        "synthetic_data_declaration": "All dashboard inputs and outputs are synthetic.",
        "responsible_use_disclaimer": (
            "Local dashboard-ready evidence only; not operational control or certified reporting."
        ),
        "known_limitations": [
            "No Power BI, Fabric, Azure, OpenAI, or external-service calls are made.",
            "No `.pbix` or live semantic model is produced.",
            "Synthetic patterns may not represent real airline operations.",
        ],
        "milestone_scope": "Milestone 10 dashboard-output layer only.",
    }


def _fieldnames(table_name: str, rows: list[dict[str, object]]) -> list[str]:
    if rows:
        return list(rows[0])
    return _EMPTY_SCHEMAS.get(table_name, ["dashboard_run_id"])


def _source_run_ids(source: Any) -> dict[str, str | None]:
    return {
        "validation": source.validation.run_id,
        "disruption_scoring": source.disruption.run_id,
        "monitoring": source.monitoring.run_id,
        **{domain: artefact.run_id for domain, artefact in source.optional.items()},
    }


def _relationships(tables: dict[str, list[dict[str, object]]]) -> list[str]:
    return [table for table in tables if table.startswith("fact_")]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_EMPTY_SCHEMAS = {
    "fact_passenger_forecast": [
        "dashboard_run_id",
        "flight_id",
        "route_id",
        "operating_date",
        "forecast_passengers",
        "forecast_lower_80",
        "forecast_upper_80",
        "actual_passengers",
        "forecast_load_factor",
        "absolute_error",
        "partition",
        "source_domain",
        "source_run_id",
    ],
    "fact_delay_prediction": [
        "dashboard_run_id",
        "flight_id",
        "route_id",
        "operating_date",
        "delay_probability",
        "predicted_delay_flag",
        "risk_band",
        "estimated_delay_minutes",
        "actual_delay_flag",
        "actual_delay_minutes",
        "partition",
        "source_domain",
        "source_run_id",
    ],
    "fact_maintenance_risk": [
        "dashboard_run_id",
        "flight_id",
        "aircraft_id",
        "aircraft_type",
        "maintenance_risk_score",
        "aircraft_health_score",
        "risk_band",
        "alert_category",
        "human_review_required",
        "source_domain",
        "source_run_id",
    ],
    "fact_monitoring_alert": [
        "dashboard_run_id",
        "monitoring_alert_id",
        "monitoring_domain",
        "severity",
        "status",
        "message",
        "source_domain",
        "source_run_id",
    ],
    "fact_assistant_response": [
        "dashboard_run_id",
        "assistant_run_id",
        "intent",
        "response_title",
        "section_title",
        "section_order",
        "evidence_reference_count",
        "guardrail_status",
        "human_review_required",
        "local_template_mode",
        "source_domain",
        "source_run_id",
    ],
}
