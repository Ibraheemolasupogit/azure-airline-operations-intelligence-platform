from __future__ import annotations

from airline_operations_intelligence.dashboard.config import load_dashboard_config
from airline_operations_intelligence.dashboard.data_dictionary import build_data_dictionary
from airline_operations_intelligence.dashboard.dimensions import build_dimensions
from airline_operations_intelligence.dashboard.facts import build_facts
from airline_operations_intelligence.dashboard.measures import build_kpis, build_summaries, measure_catalogue
from airline_operations_intelligence.dashboard.page_specs import build_page_specs
from airline_operations_intelligence.dashboard.quality import run_quality_checks
from airline_operations_intelligence.dashboard.semantic_model import build_semantic_model


def test_dashboard_table_builders_quality_and_catalogues() -> None:
    config = load_dashboard_config("configs/dashboard_outputs_ci.yaml")
    source_tables = {
        "flight_schedule": [
            {
                "flight_id": "FLT-20250101-00001",
                "flight_number": "AO1001",
                "operating_date": "2025-01-01",
                "scheduled_departure_utc": "2025-01-01T05:00:00Z",
                "origin_airport": "LHR",
                "destination_airport": "AMS",
                "route_id": "LHR-AMS",
                "aircraft_id": "SYN-A320-001",
                "aircraft_type": "A320",
                "seat_capacity": "180",
                "service_type": "scheduled",
            }
        ],
        "delay_history": [
            {
                "flight_id": "FLT-20250101-00001",
                "departure_delay_minutes": "75",
                "arrival_delay_minutes": "80",
                "cancelled_flag": "False",
                "diverted_flag": "False",
                "primary_delay_cause": "crew",
                "reactionary_delay_minutes": "10",
            }
        ],
        "passenger_demand": [
            {
                "flight_id": "FLT-20250101-00001",
                "observation_date": "2024-12-02",
                "route_id": "LHR-AMS",
                "days_before_departure": "30",
                "booked_passengers": "100",
                "expected_final_passengers": "140",
                "seat_capacity": "180",
                "load_factor": "0.78",
                "booking_velocity": "1.1",
            }
        ],
        "aircraft_health": [{"aircraft_id": "SYN-A320-001", "aircraft_type": "A320"}],
        "disruption_scores": [
            {
                "flight_id": "FLT-20250101-00001",
                "route_id": "LHR-AMS",
                "operating_date": "2025-01-01",
                "disruption_severity_score": "0.8",
                "forward_disruption_risk_score": "0.7",
                "retrospective_disruption_score": "0.8",
                "disruption_risk_band": "high",
                "recovery_priority": "urgent_review",
                "primary_disruption_driver": "crew readiness",
                "weather_component_score": "0.1",
                "delay_component_score": "0.8",
                "crew_component_score": "1.0",
                "aircraft_health_component_score": "0.2",
                "human_review_required": "True",
            }
        ],
        "monitoring_metrics": [
            {
                "monitoring_domain": "validation",
                "metric_name": "validation_invalid_record_rate",
                "metric_value": "0",
                "status": "observed",
                "severity": "info",
                "threshold": "",
                "evidence_path": "",
                "source_run_id": "unit",
            }
        ],
        "monitoring_alerts": [],
    }
    dimensions = build_dimensions("unit", source_tables, config)
    facts = build_facts("unit", source_tables, {"validation": "unit", "disruption_scoring": "unit"})
    kpis = build_kpis("unit", facts, config)
    summaries = build_summaries("unit", facts)
    tables = {**dimensions, **facts, **kpis, **summaries}
    measures = measure_catalogue()
    semantic = build_semantic_model(tables, measures, config)
    pages = build_page_specs()
    dictionary = build_data_dictionary(tables)
    checks, summary = run_quality_checks(tables, semantic, measures, pages, dictionary)

    assert dimensions["dim_date"][0]["date"] == "2025-01-01"
    assert facts["fact_flight_operations"][0]["departure_delay_minutes"] == 75.0
    assert kpis["kpi_delay_summary"][1]["metric_name"] == "material_delay_rate"
    assert summaries["route_performance_summary"][0]["route_id"] == "LHR-AMS"
    assert semantic["relationships"]
    assert len(measures) >= 10
    assert len(pages) == 8
    assert summary["failed_count"] == 0
    assert any(row["rule_id"] == "DICTIONARY-coverage" for row in checks)
