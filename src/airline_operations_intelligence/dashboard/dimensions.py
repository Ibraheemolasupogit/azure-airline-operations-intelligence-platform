"""Dimension table builders for dashboard outputs."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from airline_operations_intelligence.dashboard.config import DashboardConfig


def build_dimensions(
    run_id: str, tables: dict[str, list[dict[str, Any]]], config: DashboardConfig
) -> dict[str, list[dict[str, object]]]:
    """Build dashboard dimension tables."""
    flights = tables["flight_schedule"]
    scores = tables.get("disruption_scores", [])
    aircraft_health = tables.get("aircraft_health", [])
    start = config.semantic_model.date_table_start
    end = config.semantic_model.date_table_end
    dates = []
    current = start
    while current <= end:
        dates.append(
            {
                "dashboard_run_id": run_id,
                "date": current.isoformat(),
                "year": current.year,
                "month": current.month,
                "day": current.day,
                "day_of_week": current.isoweekday(),
                "month_name": current.strftime("%B"),
                "quarter": (current.month - 1) // 3 + 1,
                "source_domain": "semantic_model",
            }
        )
        current += timedelta(days=1)
    airports = sorted({row["origin_airport"] for row in flights} | {row["destination_airport"] for row in flights})
    routes = sorted({row["route_id"] for row in flights})
    aircraft: dict[str, dict[str, object]] = {}
    for row in flights:
        aircraft[row["aircraft_id"]] = {
            "dashboard_run_id": run_id,
            "aircraft_key": _key(config, "AIRCRAFT", row["aircraft_id"]),
            "aircraft_id": row["aircraft_id"],
            "aircraft_type": row.get("aircraft_type", ""),
            "seat_capacity": int(float(row.get("seat_capacity", 0) or 0)),
            "source_domain": "validation",
        }
    for row in aircraft_health:
        aircraft.setdefault(
            str(row.get("aircraft_id", "")),
            {
                "dashboard_run_id": run_id,
                "aircraft_key": _key(config, "AIRCRAFT", row.get("aircraft_id", "")),
                "aircraft_id": row.get("aircraft_id", ""),
                "aircraft_type": row.get("aircraft_type", ""),
                "seat_capacity": 0,
                "source_domain": "validation",
            },
        )
    service_types = sorted({row.get("service_type", "") or "Unknown" for row in flights})
    risk_bands = sorted({row.get("disruption_risk_band", "") for row in scores} | {"low", "medium", "high", "severe"})
    drivers = sorted({row.get("primary_disruption_driver", "") or "Unknown" for row in scores})
    return {
        "dim_date": dates,
        "dim_airport": [
            {
                "dashboard_run_id": run_id,
                "airport_key": _key(config, "AIRPORT", code),
                "airport_code": code,
                "airport_name": code,
                "country_code": "SYN",
                "source_domain": "validation",
            }
            for code in airports
        ],
        "dim_route": [
            {
                "dashboard_run_id": run_id,
                "route_key": _key(config, "ROUTE", route),
                "route_id": route,
                "origin_airport": route.split("-")[0] if "-" in route else "",
                "destination_airport": route.split("-")[-1] if "-" in route else "",
                "source_domain": "validation",
            }
            for route in routes
        ],
        "dim_aircraft": sorted(aircraft.values(), key=lambda row: str(row["aircraft_id"])),
        "dim_service_type": [
            {
                "dashboard_run_id": run_id,
                "service_type_key": _key(config, "SERVICE", service),
                "service_type": service,
                "service_category": service,
                "source_domain": "validation",
            }
            for service in service_types
        ],
        "dim_risk_band": [
            {
                "dashboard_run_id": run_id,
                "risk_band_key": _key(config, "RISK", band),
                "risk_band": band,
                "risk_rank": {"low": 1, "medium": 2, "high": 3, "severe": 4}.get(band, 0),
                "source_domain": "dashboard",
            }
            for band in risk_bands
            if band
        ],
        "dim_disruption_driver": [
            {
                "dashboard_run_id": run_id,
                "disruption_driver_key": _key(config, "DRIVER", driver),
                "primary_disruption_driver": driver,
                "driver_category": driver,
                "source_domain": "disruption_scoring",
            }
            for driver in drivers
        ],
    }


def _key(config: DashboardConfig, prefix: str, value: object) -> str:
    return f"{config.semantic_model.surrogate_key_prefix}_{prefix}_{str(value).replace(' ', '_').replace('-', '_')}"
