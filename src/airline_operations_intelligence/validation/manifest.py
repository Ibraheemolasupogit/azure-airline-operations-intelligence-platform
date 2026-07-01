"""Validation manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import IngestionError


def load_validation_manifest(report_dir: Path) -> dict[str, Any]:
    """Load a completed validation manifest."""
    manifest_path = report_dir / "validation-manifest.json"
    if not manifest_path.exists():
        raise IngestionError(f"Validation manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IngestionError(f"Validation manifest is not a JSON object: {manifest_path}")
    return payload
