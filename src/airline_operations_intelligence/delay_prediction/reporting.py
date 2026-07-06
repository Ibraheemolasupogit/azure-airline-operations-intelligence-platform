"""Markdown reporting for delay prediction runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from airline_operations_intelligence.common.exceptions import DelayArtefactError


def build_summary(manifest: dict[str, Any]) -> str:
    """Build delay prediction summary markdown."""
    return "\n".join(
        [
            "# Flight-Delay Prediction Summary",
            "",
            f"- Delay run: `{manifest['delay_run_id']}`",
            f"- Source validation run: `{manifest['source_validation_run_id']}`",
            f"- Champion model: `{manifest['champion_model_id']}`",
            f"- Selected threshold: `{manifest['selected_probability_threshold']}`",
            f"- Target threshold minutes: `{manifest['target']['delay_threshold_minutes']}`",
            f"- Prediction cutoff minutes: `{manifest['target']['prediction_cutoff_minutes']}`",
            f"- Partition rows: `{manifest['partition_row_counts']}`",
            f"- Overall status: `{manifest['overall_status']}`",
            "",
            "Synthetic local model only; no cloud model registration or live operations automation occurred.",
            "",
        ]
    )


def build_model_card(manifest: dict[str, Any]) -> str:
    """Build model card markdown."""
    return "\n".join(
        [
            "# Delay Model Card",
            "",
            "## Intended Use",
            "Predict whether a scheduled synthetic flight will depart at or above the configured delay threshold.",
            "",
            "## Leakage Controls",
            *[f"- {check}" for check in manifest["leakage_checks"]],
            "",
            "## Limitations",
            *[f"- {item}" for item in manifest["known_limitations"]],
            "",
        ]
    )


def build_evaluation_report(manifest: dict[str, Any]) -> str:
    """Build evaluation report markdown."""
    test = manifest["test_metrics"]
    return "\n".join(
        [
            "# Delay Prediction Evaluation",
            "",
            f"- Test PR AUC: `{test.get('pr_auc')}`",
            f"- Test ROC AUC: `{test.get('roc_auc')}`",
            f"- Test F1: `{test.get('f1')}`",
            f"- Test Brier score: `{test.get('brier_score')}`",
            "",
        ]
    )


def build_feature_availability_report(manifest: dict[str, Any]) -> str:
    """Build feature availability report markdown."""
    lines = ["# Delay Feature Availability", ""]
    for name, policy in manifest["feature_schema"]["feature_availability"].items():
        lines.append(f"- `{name}`: {policy}")
    lines.append("")
    return "\n".join(lines)


def describe_delay_prediction_report(report_dir: Path) -> str:
    """Describe a completed delay prediction report without retraining."""
    manifest_path = report_dir / "delay-prediction-manifest.json"
    if not manifest_path.is_file():
        raise DelayArtefactError(f"Delay prediction manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return "\n".join(
        [
            f"Delay prediction run: {manifest['delay_run_id']}",
            f"Source validation run: {manifest['source_validation_run_id']}",
            f"Champion model: {manifest['champion_model_id']}",
            f"Selected threshold: {manifest['selected_probability_threshold']}",
            f"Partition rows: {manifest['partition_row_counts']}",
            f"Status: {manifest['overall_status']}",
        ]
    )
