"""Generated data dictionary definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.data_generation.models import Dataset, Scalar

FIELD_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "flight_id": ("technical_identifier", "Synthetic unique flight-leg identifier."),
    "aircraft_id": ("technical_identifier", "Synthetic aircraft identifier from configured fleet."),
    "route_id": ("technical_identifier", "Configured synthetic route identifier."),
    "airport_code": ("technical_identifier", "Configured synthetic airport code."),
    "weather_event_id": ("technical_identifier", "Synthetic weather-event identifier."),
    "airport_event_id": ("technical_identifier", "Synthetic airport-event identifier."),
    "telemetry_id": ("technical_identifier", "Synthetic aircraft telemetry identifier."),
    "crew_assignment_id": ("technical_identifier", "Synthetic crew assignment identifier."),
    "booked_passengers": ("synthetic_commercial", "Synthetic booked passenger count."),
    "expected_final_passengers": ("synthetic_commercial", "Synthetic expected final passenger count."),
    "fare_class_mix": ("synthetic_commercial", "Synthetic fare-class distribution encoded as JSON."),
    "maintenance_risk_score": ("derived_metric", "Derived illustrative maintenance risk score."),
    "operational_impact_score": ("derived_metric", "Derived weather operational impact score."),
}


def build_data_dictionary(datasets: list[Dataset]) -> dict[str, Any]:
    """Build field-level documentation covering every generated field."""
    fields: list[dict[str, Any]] = []
    for dataset in datasets:
        example = dataset.records[0] if dataset.records else {}
        for field_name in dataset.field_names:
            value = example.get(field_name)
            classification, description = FIELD_DESCRIPTIONS.get(
                field_name,
                (_classify_dataset(dataset.filename), f"Synthetic field `{field_name}` from {dataset.filename}."),
            )
            fields.append(
                {
                    "dataset": dataset.filename,
                    "field_name": field_name,
                    "data_type": _data_type(value),
                    "nullable": _nullable(dataset, field_name),
                    "description": description,
                    "business_definition": description,
                    "example": value,
                    "classification": classification,
                    "contains_personal_data": False,
                }
            )
    return {
        "schema_version": "1.0",
        "synthetic_data_declaration": "No generated field contains personal data.",
        "fields": fields,
    }


def write_data_dictionary(path: Path, dictionary: dict[str, Any]) -> None:
    """Write data dictionary JSON."""
    path.write_text(json.dumps(dictionary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _data_type(value: Scalar | None) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return "string"


def _nullable(dataset: Dataset, field_name: str) -> bool:
    return any(record.get(field_name) in {"", None} for record in dataset.records)


def _classify_dataset(filename: str) -> str:
    if filename == "aircraft_health.jsonl":
        return "synthetic_telemetry"
    if filename == "passenger_demand.csv":
        return "synthetic_commercial"
    return "synthetic_operational"
