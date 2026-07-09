"""Dashboard page specification generation."""

from __future__ import annotations


def build_page_specs() -> list[dict[str, object]]:
    """Return future Power BI dashboard page specifications."""
    pages = [
        (
            "Executive Overview",
            "Executive leaders",
            ["total_flights", "severe_disruption_rate"],
            ["kpi_executive_summary", "daily_operations_summary"],
        ),
        (
            "Operations Control",
            "Operations controllers",
            ["cancelled_flights", "diverted_flights"],
            ["fact_flight_operations", "route_performance_summary"],
        ),
        (
            "Delay Risk",
            "Network performance teams",
            ["material_delay_rate", "average_delay_minutes"],
            ["fact_delay_prediction", "kpi_delay_summary"],
        ),
        (
            "Passenger Demand",
            "Revenue and capacity teams",
            ["forecast_passenger_count", "average_forecast_load_factor"],
            ["fact_passenger_forecast", "kpi_demand_summary"],
        ),
        (
            "Aircraft Health",
            "Engineering analytics teams",
            ["high_maintenance_risk_count", "human_review_count"],
            ["fact_maintenance_risk", "aircraft_performance_summary"],
        ),
        (
            "Disruption Management",
            "Recovery managers",
            ["average_disruption_score", "urgent_review_count"],
            ["fact_disruption_score", "kpi_disruption_summary"],
        ),
        (
            "Data Quality and Monitoring",
            "Platform owners",
            ["failed_check_count", "alert_count"],
            ["fact_monitoring_metric", "fact_monitoring_alert"],
        ),
        (
            "GenAI Assistant Evidence",
            "Responsible AI reviewers",
            ["assistant_response_count"],
            ["fact_assistant_response"],
        ),
    ]
    return [
        {
            "page_name": name,
            "purpose": f"Summarise synthetic {name.lower()} evidence for local dashboard review.",
            "target_users": users,
            "primary_kpis": kpis,
            "recommended_visuals": ["KPI cards", "Table", "Trend line", "Bar chart"],
            "filters": ["date", "route", "airport", "aircraft", "risk band"],
            "drill_throughs": ["flight detail", "source evidence"],
            "source_tables": tables,
            "caveats": "Synthetic local data only; not a certified operational dashboard.",
            "responsible_use_notes": "Requires human review and must not be used for real airline decisions.",
        }
        for name, users, kpis, tables in pages
    ]
