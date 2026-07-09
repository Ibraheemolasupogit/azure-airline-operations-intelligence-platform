"""Power BI semantic model specification generation."""

from __future__ import annotations

from typing import Any

from airline_operations_intelligence.dashboard.config import DashboardConfig


def build_semantic_model(
    tables: dict[str, list[dict[str, object]]], measures: list[dict[str, str]], config: DashboardConfig
) -> dict[str, Any]:
    """Build a JSON semantic-model specification for future Power BI/Fabric consumption."""
    columns = {
        table: [
            {
                "name": field,
                "data_type": _type_name(_example(rows, field)),
                "hidden": field.endswith("_key") or field == "dashboard_run_id",
                "description": f"{field} from {table}.",
            }
            for field in (list(rows[0]) if rows else [])
        ]
        for table, rows in tables.items()
    }
    return {
        "model_name": config.semantic_model.model_name,
        "currency_code": config.semantic_model.currency_code,
        "timezone": config.semantic_model.timezone,
        "date_table": {
            "table": "dim_date",
            "date_column": "date",
            "start": config.semantic_model.date_table_start.isoformat(),
            "end": config.semantic_model.date_table_end.isoformat(),
        },
        "tables": [
            {
                "name": name,
                "columns": columns[name],
                "key_columns": _key_columns(name),
                "display_folder": _folder(name),
                "description": f"Dashboard-ready {name.replace('_', ' ')} table.",
            }
            for name in sorted(tables)
        ],
        "relationships": _relationships(tables),
        "recommended_measures": measures,
        "role_playing_dimension_guidance": (
            "Use dim_airport as separate origin and destination role-playing dimensions in Power BI if "
            "bidirectional airport filtering is required."
        ),
        "filter_direction_guidance": "Prefer single-direction dimension-to-fact filtering.",
        "formatting_hints": {"rates": "0.0%", "scores": "0.000", "counts": "Whole Number"},
    }


def _relationships(tables: dict[str, list[dict[str, object]]]) -> list[dict[str, str]]:
    relationships = []
    for table, rows in tables.items():
        if not table.startswith("fact_") or not rows:
            continue
        fields = set(rows[0])
        if "operating_date" in fields:
            relationships.append(
                {"from": "dim_date[date]", "to": f"{table}[operating_date]", "cardinality": "one-to-many"}
            )
        if "route_id" in fields:
            relationships.append(
                {"from": "dim_route[route_id]", "to": f"{table}[route_id]", "cardinality": "one-to-many"}
            )
        if "aircraft_id" in fields:
            relationships.append(
                {"from": "dim_aircraft[aircraft_id]", "to": f"{table}[aircraft_id]", "cardinality": "one-to-many"}
            )
        if "disruption_risk_band" in fields:
            relationships.append(
                {
                    "from": "dim_risk_band[risk_band]",
                    "to": f"{table}[disruption_risk_band]",
                    "cardinality": "one-to-many",
                }
            )
    return relationships


def _example(rows: list[dict[str, object]], field: str) -> object:
    for row in rows:
        value = row.get(field)
        if value not in {"", None}:
            return value
    return ""


def _type_name(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int64"
    if isinstance(value, float):
        return "double"
    return "string"


def _key_columns(table: str) -> list[str]:
    if table.startswith("dim_"):
        return [
            field
            for field in (
                "date",
                "airport_code",
                "route_id",
                "aircraft_id",
                "service_type",
                "risk_band",
                "primary_disruption_driver",
            )
            if field in table or table == "dim_date"
        ]
    return []


def _folder(table: str) -> str:
    if table.startswith("dim_"):
        return "Dimensions"
    if table.startswith("kpi_"):
        return "KPI Tables"
    if table.startswith("fact_"):
        return "Facts"
    return "Summaries"
