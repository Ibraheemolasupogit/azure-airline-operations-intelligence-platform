"""Quality checks for dashboard outputs."""

from __future__ import annotations

import json
import math
from typing import Any

from airline_operations_intelligence.common.exceptions import DashboardQualityError

REQUIRED_TABLES = {
    "dim_date",
    "dim_airport",
    "dim_route",
    "dim_aircraft",
    "dim_service_type",
    "dim_risk_band",
    "dim_disruption_driver",
    "fact_flight_operations",
    "fact_passenger_demand",
    "fact_disruption_score",
    "fact_monitoring_metric",
    "fact_monitoring_alert",
    "kpi_executive_summary",
    "kpi_operations_summary",
    "kpi_delay_summary",
    "kpi_demand_summary",
    "kpi_maintenance_summary",
    "kpi_disruption_summary",
    "kpi_data_quality_summary",
    "kpi_monitoring_summary",
    "route_performance_summary",
    "airport_performance_summary",
    "aircraft_performance_summary",
    "daily_operations_summary",
}

PRIMARY_KEYS = {
    "dim_date": ["date"],
    "dim_airport": ["airport_code"],
    "dim_route": ["route_id"],
    "dim_aircraft": ["aircraft_id"],
    "fact_flight_operations": ["flight_id"],
    "fact_disruption_score": ["flight_id"],
}


def run_quality_checks(
    tables: dict[str, list[dict[str, object]]],
    semantic_model: dict[str, Any],
    measures: list[dict[str, str]],
    pages: list[dict[str, object]],
    dictionary_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run deterministic dashboard quality checks."""
    checks: list[dict[str, object]] = []
    _check_required_tables(tables, checks)
    _check_primary_keys(tables, checks)
    _check_references(tables, checks)
    _check_values(tables, checks)
    _check_semantic_model(tables, semantic_model, checks)
    _check_measures(tables, measures, checks)
    _check_pages(tables, pages, checks)
    _check_dictionary(tables, dictionary_rows, checks)
    failed = sum(1 for row in checks if row["status"] == "failed")
    summary: dict[str, object] = {
        "check_count": len(checks),
        "passed_count": len(checks) - failed,
        "failed_count": failed,
    }
    if failed:
        raise DashboardQualityError(f"Dashboard quality checks failed: {failed}")
    return checks, summary


def _add(checks: list[dict[str, object]], rule_id: str, status: str, observed: object, message: str) -> None:
    checks.append({"rule_id": rule_id, "status": status, "observed_value": observed, "message": message})


def _check_required_tables(tables: dict[str, list[dict[str, object]]], checks: list[dict[str, object]]) -> None:
    for table in sorted(REQUIRED_TABLES):
        _add(
            checks,
            f"TABLE-{table}",
            "passed" if table in tables else "failed",
            table in tables,
            "Required table exists.",
        )


def _check_primary_keys(tables: dict[str, list[dict[str, object]]], checks: list[dict[str, object]]) -> None:
    for table, fields in PRIMARY_KEYS.items():
        keys = [tuple(row.get(field) for field in fields) for row in tables.get(table, [])]
        _add(
            checks,
            f"PK-{table}",
            "passed" if len(keys) == len(set(keys)) else "failed",
            len(keys),
            "Primary keys are unique.",
        )


def _check_references(tables: dict[str, list[dict[str, object]]], checks: list[dict[str, object]]) -> None:
    routes = {row["route_id"] for row in tables.get("dim_route", [])}
    aircraft = {row["aircraft_id"] for row in tables.get("dim_aircraft", [])}
    bad_routes = [row.get("route_id") for row in tables["fact_flight_operations"] if row.get("route_id") not in routes]
    bad_aircraft = [
        row.get("aircraft_id") for row in tables["fact_flight_operations"] if row.get("aircraft_id") not in aircraft
    ]
    _add(
        checks,
        "FK-route",
        "passed" if not bad_routes else "failed",
        len(bad_routes),
        "Flight route references resolve.",
    )
    _add(
        checks,
        "FK-aircraft",
        "passed" if not bad_aircraft else "failed",
        len(bad_aircraft),
        "Flight aircraft references resolve.",
    )


def _check_values(tables: dict[str, list[dict[str, object]]], checks: list[dict[str, object]]) -> None:
    bad = 0
    for rows in tables.values():
        for row in rows:
            for value in row.values():
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    bad += 1
    _add(checks, "VALUES-finite", "passed" if bad == 0 else "failed", bad, "No NaN or infinity values.")


def _check_semantic_model(
    tables: dict[str, list[dict[str, object]]], model: dict[str, Any], checks: list[dict[str, object]]
) -> None:
    table_names = {table["name"] for table in model.get("tables", []) if isinstance(table, dict)}
    _add(
        checks,
        "SEMANTIC-tables",
        "passed" if table_names <= set(tables) else "failed",
        sorted(table_names - set(tables)),
        "Semantic model references existing tables.",
    )
    json.dumps(model)
    _add(checks, "SEMANTIC-json", "passed", True, "Semantic model JSON parses.")


def _check_measures(
    tables: dict[str, list[dict[str, object]]], measures: list[dict[str, str]], checks: list[dict[str, object]]
) -> None:
    missing = [measure["source_table"] for measure in measures if measure["source_table"] not in tables]
    _add(
        checks,
        "MEASURE-source-tables",
        "passed" if not missing else "failed",
        missing,
        "Measure catalogue references existing tables.",
    )


def _check_pages(
    tables: dict[str, list[dict[str, object]]], pages: list[dict[str, object]], checks: list[dict[str, object]]
) -> None:
    missing: list[object] = []
    for page in pages:
        source_tables = page.get("source_tables", [])
        if isinstance(source_tables, list):
            missing.extend(table for table in source_tables if table not in tables)
    _add(
        checks,
        "PAGES-source-tables",
        "passed" if not missing else "failed",
        missing,
        "Page specs reference existing tables.",
    )


def _check_dictionary(
    tables: dict[str, list[dict[str, object]]], rows: list[dict[str, object]], checks: list[dict[str, object]]
) -> None:
    documented = {(row["table_name"], row["field_name"]) for row in rows}
    missing = []
    for table, table_rows in tables.items():
        for field in list(table_rows[0]) if table_rows else []:
            if (table, field) not in documented:
                missing.append(f"{table}.{field}")
    _add(
        checks,
        "DICTIONARY-coverage",
        "passed" if not missing else "failed",
        len(missing),
        "Data dictionary covers every generated field.",
    )
