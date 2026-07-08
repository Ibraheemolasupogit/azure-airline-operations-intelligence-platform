from __future__ import annotations

from pathlib import Path

from airline_operations_intelligence.monitoring.alerts import generate_monitoring_alerts
from airline_operations_intelligence.monitoring.checks import run_monitoring_checks
from airline_operations_intelligence.monitoring.config import parse_monitoring_config
from airline_operations_intelligence.monitoring.contracts import MonitoringInput, MonitoringSource
from airline_operations_intelligence.monitoring.drift import compare_drift
from airline_operations_intelligence.monitoring.metrics import extract_metrics
from airline_operations_intelligence.monitoring.summaries import domain_health_summary, platform_health_summary


def test_monitoring_metrics_checks_alerts_and_summaries() -> None:
    config = parse_monitoring_config(_raw_config())
    source = _source(disruption_severe=7)

    metrics = extract_metrics(source)
    checks = run_monitoring_checks(source, metrics, config, "2025-01-01T00:00:00Z")
    alerts = generate_monitoring_alerts("monitoring-a", checks, config)

    assert {metric.monitoring_domain for metric in metrics} == {"generation", "validation", "disruption_scoring"}
    assert any(check.rule_id == "MON-DISR-002" and check.status == "warning" for check in checks)
    assert [alert.rule_id for alert in alerts] == ["MON-DISR-002"]
    domain_rows = domain_health_summary(
        "monitoring-a",
        metrics,
        checks,
        alerts,
        {"generation": "gen-a", "validation": "val-a", "disruption_scoring": "disr-a"},
        {"generation": "generation-manifest.json", "validation": "validation-manifest.json"},
    )
    platform_rows = platform_health_summary("monitoring-a", domain_rows, checks, alerts, "2025-01-01T00:00:00Z")
    assert platform_rows[0]["warning_check_count"] == 1
    assert platform_rows[0]["alert_count"] == 1


def test_drift_skips_without_baseline_and_handles_zero_baseline() -> None:
    config = parse_monitoring_config(_raw_config())
    metrics = extract_metrics(_source(disruption_severe=0))

    skipped = compare_drift(metrics, None, config)
    assert skipped[0].status == "skipped"

    baseline = {
        "metric_values": [
            {
                "monitoring_domain": "disruption_scoring",
                "metric_name": "disruption_severe_rate",
                "metric_value": 0,
            }
        ]
    }
    compared = compare_drift(
        [metric for metric in metrics if metric.metric_name == "disruption_severe_rate"],
        baseline,
        config,
    )
    assert compared[0].relative_change == 0


def test_alerts_are_limited_and_sorted_by_severity() -> None:
    raw = _raw_config()
    raw["monitoring"]["maximum_alerts_per_run"] = 1
    config = parse_monitoring_config(raw)
    checks = run_monitoring_checks(
        _source(disruption_severe=24), extract_metrics(_source(disruption_severe=24)), config, "t"
    )

    alerts = generate_monitoring_alerts("monitoring-b", checks, config)

    assert len(alerts) == 1
    assert alerts[0].severity in {"warning", "critical"}


def _source(disruption_severe: int) -> MonitoringSource:
    generation = {
        "run_id": "gen-a",
        "datasets": [{"filename": "flight_schedule.csv", "row_count": 24, "sha256": "x"}],
        "anomaly_counts": {"review": 1},
        "cancellation_counts": {"cancelled": 0},
        "diversion_counts": {"diverted": 0},
    }
    validation = {
        "validation_run_id": "val-a",
        "overall_status": "passed",
        "source_generation_run_id": "gen-a",
        "source_row_count": 24,
        "valid_row_count": 24,
        "quarantined_row_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "fatal_count": 0,
        "datasets": [{"processed_filename": "flight_schedule.csv"}],
    }
    disruption = {
        "disruption_run_id": "disr-a",
        "source_validation_run_id": "val-a",
        "overall_status": "passed",
        "row_counts": {"scores": 24, "alerts": 2},
        "risk_band_counts": {"severe": disruption_severe, "high": 1},
        "recovery_priority_counts": {"urgent_review": disruption_severe},
        "component_score_summary": {"delay": {"average": 0.5, "maximum": 0.9}},
    }
    accepted = [
        MonitoringInput(
            "generation",
            "gen-a",
            Path("data/raw/gen-a"),
            Path("generation-manifest.json"),
            "x",
            "accepted",
            True,
            "accepted",
        ),
        MonitoringInput(
            "validation",
            "val-a",
            Path("reports/validation/val-a"),
            Path("validation-manifest.json"),
            "y",
            "accepted",
            True,
            "accepted",
        ),
        MonitoringInput(
            "disruption_scoring",
            "disr-a",
            Path("reports/disruption/disr-a"),
            Path("disruption-scoring-manifest.json"),
            "z",
            "accepted",
            True,
            "accepted",
        ),
    ]
    return MonitoringSource(
        validation_run_id="val-a",
        validation_report_dir=Path("reports/validation/val-a"),
        validation_manifest_path=Path("validation-manifest.json"),
        validation_manifest=validation,
        generation_run_id="gen-a",
        generation_run_dir=Path("data/raw/gen-a"),
        generation_manifest_path=Path("generation-manifest.json"),
        generation_manifest=generation,
        optional_manifests={"disruption_scoring": disruption},
        optional_report_dirs={"disruption_scoring": Path("reports/disruption/disr-a")},
        baseline_report_dir=None,
        baseline_manifest=None,
        accepted_inputs=accepted,
        rejected_inputs=[],
        input_manifest_checksums={"generation": "x", "validation": "y", "disruption_scoring": "z"},
        input_artefact_checksums_verified={"generation": True, "validation": True, "disruption_scoring": True},
    )


def _raw_config() -> dict:
    from tests.unit.test_monitoring_config import _raw_config as raw_config

    return raw_config()
