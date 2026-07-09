"""Typed contracts for dashboard-output runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DashboardRunResult:
    """Result returned by the dashboard-output pipeline."""

    dashboard_run_id: str
    source_validation_run_id: str
    source_disruption_run_id: str
    source_monitoring_run_id: str
    output_dir: Path
    report_dir: Path
    manifest_path: Path
    overall_status: str
    row_counts: dict[str, int]


@dataclass(frozen=True)
class SourceArtefact:
    """A verified source domain and its manifest."""

    domain: str
    report_dir: Path
    output_dir: Path | None
    manifest_path: Path
    manifest: dict[str, Any]
    run_id: str
    validation_run_id: str | None
    manifest_sha256: str
    artefact_checksums_verified: bool


@dataclass(frozen=True)
class DashboardSource:
    """All explicit source inputs accepted by a dashboard build."""

    validation: SourceArtefact
    disruption: SourceArtefact
    monitoring: SourceArtefact
    optional: dict[str, SourceArtefact]
    generation_run_dir: Path | None
    processed_dir: Path

    @property
    def validation_run_id(self) -> str:
        """Return the governed validation run ID."""
        return self.validation.run_id


TableMap = dict[str, list[dict[str, object]]]
