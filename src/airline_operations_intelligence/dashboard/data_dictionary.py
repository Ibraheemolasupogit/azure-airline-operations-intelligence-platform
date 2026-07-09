"""Dashboard data dictionary generation."""

from __future__ import annotations


def build_data_dictionary(tables: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    """Build field-level data dictionary rows for every exported table."""
    rows: list[dict[str, object]] = []
    for table_name in sorted(tables):
        fields = list(tables[table_name][0]) if tables[table_name] else _SCHEMA_HINTS.get(table_name, [])
        for field in fields:
            rows.append(
                {
                    "table_name": table_name,
                    "field_name": field,
                    "data_type": _type_name(_example(tables[table_name], field)),
                    "nullable": True,
                    "description": f"{field.replace('_', ' ').title()} for {table_name}.",
                    "business_definition": (
                        f"Dashboard analytical field {field} sourced for local Power BI-ready outputs."
                    ),
                    "source_domain": _source_domain(table_name),
                    "source_field": field,
                    "transformation_logic": (
                        "Deterministic projection, aggregation, or documented calculation from verified source "
                        "artefacts."
                    ),
                    "classification": "synthetic operational analytics",
                    "power_bi_role": _role(table_name, field),
                    "example_value": _example(tables[table_name], field),
                }
            )
    return rows


def dictionary_markdown(rows: list[dict[str, object]]) -> str:
    """Render a compact markdown data dictionary."""
    lines = [
        "# Dashboard Data Dictionary",
        "",
        "| Table | Field | Type | Source | Definition |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['table_name']} | {row['field_name']} | {row['data_type']} | "
            f"{row['source_domain']} | {row['business_definition']} |"
        )
    return "\n".join(lines) + "\n"


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
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def _source_domain(table: str) -> str:
    if "monitoring" in table:
        return "monitoring"
    if "disruption" in table:
        return "disruption_scoring"
    if "maintenance" in table:
        return "maintenance_analytics"
    if "forecast" in table:
        return "passenger_forecasting"
    if "assistant" in table:
        return "genai_assistant"
    return "validation"


def _role(table: str, field: str) -> str:
    if table.startswith("dim_"):
        return "dimension attribute"
    if field.endswith("_id") or field.endswith("_key"):
        return "relationship key"
    if field.startswith("metric_") or field.endswith("_count") or field.endswith("_rate") or field.endswith("_score"):
        return "measure input"
    return "fact attribute"


_SCHEMA_HINTS = {
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
