"""Dataset readers for maintenance analytics."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read CSV rows."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_jsonl(path: Path) -> list[dict[str, object]]:
    """Read JSONL rows."""
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]
