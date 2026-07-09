"""Dashboard KPI and measure catalogue generation."""

from __future__ import annotations

from collections import Counter

from airline_operations_intelligence.dashboard.config import DashboardConfig

KPI_TABLES = [
    "kpi_executive_summary",
    "kpi_operations_summary",
    "kpi_delay_summary",
    "kpi_demand_summary",
    "kpi_maintenance_summary",
    "kpi_disruption_summary",
    "kpi_data_quality_summary",
    "kpi_monitoring_summary",
]


def build_kpis(
    run_id: str, facts: dict[str, list[dict[str, object]]], config: DashboardConfig
) -> dict[str, list[dict[str, object]]]:
    """Build dashboard KPI tables."""
    flights = facts["fact_flight_operations"]
    disruptions = facts["fact_disruption_score"]
    monitoring = facts["fact_monitoring_metric"]
    alerts = facts["fact_monitoring_alert"]
    delays = facts["fact_delay_prediction"]
    demand = facts["fact_passenger_forecast"]
    maintenance = facts["fact_maintenance_risk"]
    total = len(flights)
    cancelled = sum(1 for row in flights if row["cancelled_flag"])
    diverted = sum(1 for row in flights if row["diverted_flag"])
    severe = sum(1 for row in disruptions if row["disruption_risk_band"] in {"high", "severe"})
    high_delay = sum(1 for row in flights if _number(row["departure_delay_minutes"]) >= 60)
    failed_checks = sum(1 for row in monitoring if row["status"] in {"failed", "error"})
    warning_checks = sum(1 for row in monitoring if row["status"] == "warning")
    validation_invalid_rate = _metric_lookup(monitoring, "validation_invalid_record_rate")
    kpis = {
        "kpi_executive_summary": [
            _kpi(
                run_id, "total_flights", total, total, total, "passed", "", "validation", "Scheduled synthetic flights."
            ),
            _kpi(
                run_id,
                "cancelled_flights",
                cancelled,
                cancelled,
                total,
                "observed",
                "",
                "validation",
                "Cancelled synthetic flights.",
            ),
            _kpi(
                run_id,
                "diverted_flights",
                diverted,
                diverted,
                total,
                "observed",
                "",
                "validation",
                "Diverted synthetic flights.",
            ),
            _kpi(
                run_id,
                "average_departure_delay",
                _avg(flights, "departure_delay_minutes"),
                "",
                total,
                "observed",
                "",
                "validation",
                "Average departure delay minutes.",
            ),
            _kpi(
                run_id,
                "severe_disruption_count",
                severe,
                severe,
                len(disruptions),
                "warning"
                if _rate(severe, len(disruptions)) > config.kpi_thresholds["severe_disruption_rate"]
                else "passed",
                config.kpi_thresholds["severe_disruption_rate"],
                "disruption_scoring",
                "High or severe disruption flights.",
            ),
            _kpi(
                run_id,
                "severe_disruption_rate",
                _rate(severe, len(disruptions)),
                severe,
                len(disruptions),
                "observed",
                config.kpi_thresholds["severe_disruption_rate"],
                "disruption_scoring",
                "High/severe disruptions divided by scored flights.",
            ),
            _kpi(
                run_id,
                "monitoring_highest_severity",
                _highest_severity(monitoring),
                "",
                "",
                "observed",
                "",
                "monitoring",
                "Highest monitoring severity.",
            ),
            _kpi(
                run_id,
                "validation_invalid_record_rate",
                validation_invalid_rate,
                "",
                "",
                "warning"
                if validation_invalid_rate > config.kpi_thresholds["validation_invalid_rate_warning"]
                else "passed",
                config.kpi_thresholds["validation_invalid_rate_warning"],
                "monitoring",
                "Invalid validation records divided by source records.",
            ),
        ],
        "kpi_operations_summary": [
            _kpi(
                run_id, "total_flights", total, total, total, "passed", "", "validation", "Scheduled synthetic flights."
            ),
            _kpi(
                run_id,
                "cancelled_flights",
                cancelled,
                cancelled,
                total,
                "observed",
                "",
                "validation",
                "Cancelled synthetic flights.",
            ),
            _kpi(
                run_id,
                "diverted_flights",
                diverted,
                diverted,
                total,
                "observed",
                "",
                "validation",
                "Diverted synthetic flights.",
            ),
        ],
        "kpi_delay_summary": [
            _kpi(
                run_id,
                "material_delay_count",
                high_delay,
                high_delay,
                total,
                "observed",
                config.kpi_thresholds["high_delay_rate"],
                "validation",
                "Flights delayed by at least 60 minutes.",
            ),
            _kpi(
                run_id,
                "material_delay_rate",
                _rate(high_delay, total),
                high_delay,
                total,
                "warning" if _rate(high_delay, total) > config.kpi_thresholds["high_delay_rate"] else "passed",
                config.kpi_thresholds["high_delay_rate"],
                "validation",
                "Material delayed flights divided by flights.",
            ),
            _kpi(
                run_id,
                "average_delay_minutes",
                _avg(flights, "departure_delay_minutes"),
                "",
                total,
                "observed",
                "",
                "validation",
                "Average departure delay minutes.",
            ),
            _kpi(
                run_id,
                "delay_prediction_high_risk_count",
                sum(1 for row in delays if row["risk_band"] in {"high", "severe"}),
                "",
                len(delays),
                "observed",
                "",
                "delay_prediction",
                "High-risk delay predictions.",
            ),
            _kpi(
                run_id,
                "false_positive_count",
                sum(1 for row in delays if row["predicted_delay_flag"] and not row["actual_delay_flag"]),
                "",
                len(delays),
                "observed",
                "",
                "delay_prediction",
                "Predicted delay where actual flag is false.",
            ),
        ],
        "kpi_demand_summary": [
            _kpi(
                run_id,
                "forecast_passenger_count",
                sum(_number(row["forecast_passengers"]) for row in demand),
                "",
                len(demand),
                "observed",
                "",
                "passenger_forecasting",
                "Forecast passenger total.",
            ),
            _kpi(
                run_id,
                "average_forecast_load_factor",
                _avg(demand, "forecast_load_factor"),
                "",
                len(demand),
                "observed",
                "",
                "passenger_forecasting",
                "Average forecast load factor.",
            ),
            _kpi(
                run_id,
                "capacity_pressure_flight_count",
                sum(1 for row in demand if _number(row["forecast_load_factor"]) > 0.9),
                "",
                len(demand),
                "observed",
                "",
                "passenger_forecasting",
                "Flights above 90 percent forecast load factor.",
            ),
        ],
        "kpi_maintenance_summary": [
            _kpi(
                run_id,
                "aircraft_count",
                len({row["aircraft_id"] for row in maintenance}),
                "",
                len(maintenance),
                "observed",
                "",
                "maintenance_analytics",
                "Aircraft represented in maintenance facts.",
            ),
            _kpi(
                run_id,
                "high_maintenance_risk_count",
                sum(1 for row in maintenance if row["risk_band"] in {"high", "critical"}),
                "",
                len(maintenance),
                "observed",
                config.kpi_thresholds["high_maintenance_risk_rate"],
                "maintenance_analytics",
                "High maintenance risk rows.",
            ),
            _kpi(
                run_id,
                "max_maintenance_risk_score",
                max([_number(row["maintenance_risk_score"]) for row in maintenance] or [0]),
                "",
                len(maintenance),
                "observed",
                "",
                "maintenance_analytics",
                "Maximum maintenance risk score.",
            ),
            _kpi(
                run_id,
                "human_review_count",
                sum(1 for row in maintenance if row["human_review_required"]),
                "",
                len(maintenance),
                "observed",
                "",
                "maintenance_analytics",
                "Maintenance rows requiring human review.",
            ),
        ],
        "kpi_disruption_summary": [
            _kpi(
                run_id,
                "average_disruption_score",
                _avg(disruptions, "disruption_severity_score"),
                "",
                len(disruptions),
                "observed",
                "",
                "disruption_scoring",
                "Average disruption severity score.",
            ),
            _kpi(
                run_id,
                "max_disruption_score",
                max([_number(row["disruption_severity_score"]) for row in disruptions] or [0]),
                "",
                len(disruptions),
                "observed",
                "",
                "disruption_scoring",
                "Maximum disruption score.",
            ),
            _kpi(
                run_id,
                "urgent_review_count",
                sum(1 for row in disruptions if row["recovery_priority"] == "urgent_review"),
                "",
                len(disruptions),
                "observed",
                "",
                "disruption_scoring",
                "Urgent recovery review rows.",
            ),
            _kpi(
                run_id,
                "dominant_disruption_driver",
                _mode([str(row["primary_disruption_driver"]) for row in disruptions]),
                "",
                "",
                "observed",
                "",
                "disruption_scoring",
                "Most frequent disruption driver.",
            ),
        ],
        "kpi_data_quality_summary": [
            _kpi(
                run_id,
                "validation_invalid_record_rate",
                validation_invalid_rate,
                "",
                "",
                "passed",
                config.kpi_thresholds["validation_invalid_rate_warning"],
                "monitoring",
                "Validation invalid record rate.",
            ),
            _kpi(
                run_id,
                "monitoring_failed_check_count",
                failed_checks,
                failed_checks,
                len(monitoring),
                "passed" if failed_checks == 0 else "failed",
                "",
                "monitoring",
                "Failed monitoring checks.",
            ),
        ],
        "kpi_monitoring_summary": [
            _kpi(
                run_id,
                "check_count",
                len(monitoring),
                len(monitoring),
                len(monitoring),
                "observed",
                "",
                "monitoring",
                "Monitoring metric count.",
            ),
            _kpi(
                run_id,
                "failed_check_count",
                failed_checks,
                failed_checks,
                len(monitoring),
                "passed" if failed_checks == 0 else "failed",
                "",
                "monitoring",
                "Failed checks.",
            ),
            _kpi(
                run_id,
                "warning_check_count",
                warning_checks,
                warning_checks,
                len(monitoring),
                "observed",
                "",
                "monitoring",
                "Warning checks.",
            ),
            _kpi(
                run_id,
                "alert_count",
                len(alerts),
                len(alerts),
                len(alerts),
                "observed",
                config.kpi_thresholds["monitoring_alert_rate_warning"],
                "monitoring",
                "Monitoring alerts.",
            ),
            _kpi(
                run_id,
                "critical_alert_count",
                sum(1 for row in alerts if row["severity"] == "critical"),
                "",
                len(alerts),
                "observed",
                "",
                "monitoring",
                "Critical monitoring alerts.",
            ),
            _kpi(
                run_id,
                "platform_health_status",
                _highest_severity(monitoring),
                "",
                "",
                "observed",
                "",
                "monitoring",
                "Platform health signal.",
            ),
        ],
    }
    return kpis


def build_summaries(run_id: str, facts: dict[str, list[dict[str, object]]]) -> dict[str, list[dict[str, object]]]:
    """Build route, airport, aircraft, and daily dashboard summaries."""
    flights = facts["fact_flight_operations"]
    disruptions = {row["flight_id"]: row for row in facts["fact_disruption_score"]}
    return {
        "route_performance_summary": _group_summary(run_id, flights, disruptions, "route_id", "route_id"),
        "airport_performance_summary": _airport_summary(run_id, flights),
        "aircraft_performance_summary": _group_summary(run_id, flights, disruptions, "aircraft_id", "aircraft_id"),
        "daily_operations_summary": _group_summary(run_id, flights, disruptions, "operating_date", "operating_date"),
    }


def measure_catalogue() -> list[dict[str, str]]:
    """Return documented Power BI-style measure recommendations."""
    return [
        _measure(
            "Total Flights",
            "COUNTROWS(fact_flight_operations)",
            "fact_flight_operations",
            "Whole Number",
            "Executive",
            "Scheduled synthetic flight count.",
        ),
        _measure(
            "Cancelled Flights",
            "CALCULATE([Total Flights], fact_flight_operations[cancelled_flag] = TRUE())",
            "fact_flight_operations",
            "Whole Number",
            "Operations",
            "Cancelled synthetic flights.",
        ),
        _measure(
            "Cancellation Rate",
            "DIVIDE([Cancelled Flights], [Total Flights])",
            "fact_flight_operations",
            "0.0%",
            "Operations",
            "Cancelled flights divided by total flights.",
        ),
        _measure(
            "Diverted Flights",
            "CALCULATE([Total Flights], fact_flight_operations[diverted_flag] = TRUE())",
            "fact_flight_operations",
            "Whole Number",
            "Operations",
            "Diverted synthetic flights.",
        ),
        _measure(
            "Average Departure Delay",
            "AVERAGE(fact_flight_operations[departure_delay_minutes])",
            "fact_flight_operations",
            "0.0",
            "Delay",
            "Average departure delay minutes.",
        ),
        _measure(
            "Material Delay Rate",
            (
                "DIVIDE(COUNTROWS(FILTER(fact_flight_operations, "
                "fact_flight_operations[departure_delay_minutes] >= 60)), [Total Flights])"
            ),
            "fact_flight_operations",
            "0.0%",
            "Delay",
            "Rate of flights delayed at least 60 minutes.",
        ),
        _measure(
            "Average Disruption Score",
            "AVERAGE(fact_disruption_score[disruption_severity_score])",
            "fact_disruption_score",
            "0.000",
            "Disruption",
            "Average disruption score.",
        ),
        _measure(
            "Severe Disruption Rate",
            (
                "DIVIDE(COUNTROWS(FILTER(fact_disruption_score, "
                'fact_disruption_score[disruption_risk_band] IN {"high","severe"})), '
                "COUNTROWS(fact_disruption_score))"
            ),
            "fact_disruption_score",
            "0.0%",
            "Disruption",
            "High/severe disruptions divided by scored flights.",
        ),
        _measure(
            "Monitoring Alert Count",
            "COUNTROWS(fact_monitoring_alert)",
            "fact_monitoring_alert",
            "Whole Number",
            "Monitoring",
            "Monitoring alert rows.",
        ),
        _measure(
            "Validation Invalid Record Rate",
            "MAX(kpi_data_quality_summary[metric_value])",
            "kpi_data_quality_summary",
            "0.0%",
            "Quality",
            "Validation invalid record rate from monitoring evidence.",
        ),
        _measure(
            "Maintenance Alert Count",
            'COUNTROWS(FILTER(fact_maintenance_risk, fact_maintenance_risk[alert_category] <> "none"))',
            "fact_maintenance_risk",
            "Whole Number",
            "Maintenance",
            "Maintenance alert-like rows.",
        ),
        _measure(
            "Forecast WAPE",
            "DIVIDE(SUM(fact_passenger_forecast[absolute_error]), SUM(fact_passenger_forecast[actual_passengers]))",
            "fact_passenger_forecast",
            "0.0%",
            "Demand",
            "Forecast weighted absolute percentage error.",
        ),
        _measure(
            "Assistant Response Count",
            "DISTINCTCOUNT(fact_assistant_response[assistant_run_id])",
            "fact_assistant_response",
            "Whole Number",
            "Assistant",
            "Assistant responses available for evidence pages.",
        ),
    ]


def _kpi(
    run_id: str,
    name: str,
    value: object,
    numerator: object,
    denominator: object,
    status: str,
    threshold: object,
    domain: str,
    definition: str,
) -> dict[str, object]:
    return {
        "dashboard_run_id": run_id,
        "metric_name": name,
        "metric_value": value,
        "numerator": numerator,
        "denominator": denominator,
        "status": status,
        "threshold": threshold,
        "source_domain": domain,
        "source_run_id": "",
        "business_definition": definition,
    }


def _measure(name: str, expression: str, table: str, fmt: str, folder: str, definition: str) -> dict[str, str]:
    return {
        "measure_name": name,
        "business_definition": definition,
        "dax_expression": expression,
        "source_table": table,
        "format_string": fmt,
        "display_folder": folder,
        "caveats": "Documentation only; DAX is not executed by this local workflow.",
    }


def _avg(rows: list[dict[str, object]], field: str) -> float:
    values = [_number(row[field]) for row in rows if row.get(field) not in {"", None}]
    return round(sum(values) / len(values), 6) if values else 0.0


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _mode(values: list[str]) -> str:
    return Counter(values).most_common(1)[0][0] if values else ""


def _highest_severity(rows: list[dict[str, object]]) -> str:
    order = {"info": 0, "warning": 1, "high": 2, "critical": 3}
    return max(
        (str(row.get("severity", "info")) for row in rows), key=lambda severity: order.get(severity, 0), default="info"
    )


def _metric_lookup(rows: list[dict[str, object]], metric_name: str) -> float:
    for row in rows:
        if row.get("metric_name") == metric_name:
            return _number(row.get("metric_value") or 0)
    return 0.0


def _group_summary(
    run_id: str,
    flights: list[dict[str, object]],
    disruptions: dict[object, dict[str, object]],
    field: str,
    output_field: str,
) -> list[dict[str, object]]:
    groups = sorted({str(row[field]) for row in flights})
    rows = []
    for value in groups:
        group = [row for row in flights if str(row[field]) == value]
        scored = [disruptions[row["flight_id"]] for row in group if row["flight_id"] in disruptions]
        rows.append(
            {
                "dashboard_run_id": run_id,
                output_field: value,
                "flight_count": len(group),
                "cancelled_flight_count": sum(1 for row in group if row["cancelled_flag"]),
                "average_departure_delay": _avg(group, "departure_delay_minutes"),
                "average_disruption_score": _avg(scored, "disruption_severity_score"),
                "high_disruption_count": sum(1 for row in scored if row["disruption_risk_band"] in {"high", "severe"}),
            }
        )
    return rows


def _airport_summary(run_id: str, flights: list[dict[str, object]]) -> list[dict[str, object]]:
    airports = sorted(
        {str(row["origin_airport"]) for row in flights} | {str(row["destination_airport"]) for row in flights}
    )
    return [
        {
            "dashboard_run_id": run_id,
            "airport_code": airport,
            "departure_flight_count": sum(1 for row in flights if row["origin_airport"] == airport),
            "arrival_flight_count": sum(1 for row in flights if row["destination_airport"] == airport),
            "average_departure_delay": _avg(
                [row for row in flights if row["origin_airport"] == airport], "departure_delay_minutes"
            ),
            "cancelled_flight_count": sum(
                1 for row in flights if row["origin_airport"] == airport and row["cancelled_flag"]
            ),
        }
        for airport in airports
    ]


def _number(value: object) -> float:
    return float(str(value or 0))
