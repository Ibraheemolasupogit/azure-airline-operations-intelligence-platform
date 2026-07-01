"""Conservative source record normalization."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from math import isfinite
from typing import Any

from airline_operations_intelligence.validation.models import FieldSpec, NormalizedRecord, RawRecord, Scalar

TRUE_VALUES = {"true", "True", "TRUE"}
FALSE_VALUES = {"false", "False", "FALSE"}


def normalize_record(raw: RawRecord, fields: tuple[FieldSpec, ...]) -> tuple[NormalizedRecord, list[str]]:
    """Normalize one raw record and return field-level error messages."""
    normalized: dict[str, Scalar] = {}
    errors: list[str] = []
    for field in fields:
        value = raw.data.get(field.name)
        parsed, error = normalize_value(value, field)
        normalized[field.name] = parsed
        if error:
            errors.append(error)
    return NormalizedRecord(dataset=raw.dataset, row_number=raw.row_number, data=normalized), errors


def normalize_value(value: Any, field: FieldSpec) -> tuple[Scalar, str | None]:
    """Normalize a scalar value according to a field contract."""
    if value is None or value == "":
        if field.nullable:
            return None, None
        return None, f"{field.name} is required"
    if isinstance(value, str):
        value = value.strip()
        if value == "" and field.nullable:
            return None, None
    try:
        if field.column_type == "string":
            parsed: Scalar = str(value)
        elif field.column_type == "integer":
            if isinstance(value, bool):
                raise ValueError("boolean is not an integer")
            parsed = int(str(value))
        elif field.column_type == "number":
            parsed = float(str(value))
            if not isfinite(parsed):
                raise ValueError("number is not finite")
        elif field.column_type == "boolean":
            parsed = _parse_bool(value)
        elif field.column_type == "timestamp":
            parsed = _parse_timestamp(str(value))
        elif field.column_type == "date":
            parsed = date.fromisoformat(str(value)).isoformat()
        elif field.column_type == "json_string":
            payload = json.loads(str(value))
            if not isinstance(payload, dict):
                raise ValueError("JSON payload must be an object")
            parsed = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        else:
            parsed = str(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, f"{field.name} cannot be parsed as {field.column_type}: {exc}"
    if field.enum is not None and str(parsed) not in field.enum:
        return parsed, f"{field.name} must be one of {sorted(field.enum)}"
    if isinstance(parsed, int | float) and not isinstance(parsed, bool):
        if field.minimum is not None and float(parsed) < field.minimum:
            return parsed, f"{field.name} must be >= {field.minimum}"
        if field.maximum is not None and float(parsed) > field.maximum:
            return parsed, f"{field.name} must be <= {field.maximum}"
    return parsed, None


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value)
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError("expected true or false")


def _parse_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
