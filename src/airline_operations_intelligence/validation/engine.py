"""Governed validation rule execution."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import cast

from airline_operations_intelligence.ingestion.normalization import normalize_record
from airline_operations_intelligence.ingestion.readers import count_source_rows
from airline_operations_intelligence.validation.config import ValidationConfig
from airline_operations_intelligence.validation.models import (
    DatasetContract,
    DatasetValidationOutput,
    NormalizedRecord,
    RawRecord,
    Severity,
    SourceRun,
    ValidationResult,
)
from airline_operations_intelligence.validation.schemas import contracts_by_name


def validate_source_records(
    source_run: SourceRun,
    raw_records: dict[str, list[RawRecord]],
    config: ValidationConfig,
    timestamp_utc: str,
) -> tuple[dict[str, DatasetValidationOutput], list[ValidationResult]]:
    """Execute schema, primary-key, business, and relationship validation."""
    contracts = contracts_by_name()
    outputs: dict[str, DatasetValidationOutput] = {}
    dataset_level_results = _manifest_results(source_run, raw_records, config, timestamp_utc)
    normalized_by_dataset: dict[str, list[NormalizedRecord]] = {}
    record_results: dict[tuple[str, int], list[ValidationResult]] = defaultdict(list)
    for dataset, contract in contracts.items():
        normalized_records = []
        results = _schema_results(contract, raw_records[dataset], config, timestamp_utc)
        for result in results:
            if result.row_number is not None:
                record_results[(dataset, result.row_number)].append(result)
        for raw in raw_records[dataset]:
            normalized, errors = normalize_record(raw, contract.fields)
            normalized_records.append(normalized)
            for error in errors:
                result = _result(
                    rule_id=f"{_prefix(dataset)}-SCHEMA",
                    dataset=dataset,
                    record=normalized,
                    field_name=error.split(" ", 1)[0],
                    severity="error",
                    category="schema",
                    message=error,
                    observed_value=None,
                    expected_condition="field parses according to declared schema",
                    timestamp_utc=timestamp_utc,
                )
                record_results[(dataset, raw.row_number)].append(result)
        normalized_by_dataset[dataset] = normalized_records
    for dataset, contract in contracts.items():
        for result in _primary_key_results(contract, normalized_by_dataset[dataset], timestamp_utc):
            if result.row_number is not None:
                record_results[(dataset, result.row_number)].append(result)
    for dataset, contract in contracts.items():
        for result in _business_results(contract, normalized_by_dataset, source_run, config, timestamp_utc):
            if result.row_number is not None:
                record_results[(dataset, result.row_number)].append(result)
    for result in _relationship_results(normalized_by_dataset, source_run, timestamp_utc):
        if result.row_number is not None:
            record_results[(result.dataset, result.row_number)].append(result)
    for dataset in contracts:
        dataset_results = []
        valid_records = []
        quarantined_records = []
        for record in normalized_by_dataset[dataset]:
            failures = [result for result in record_results[(dataset, record.row_number)] if not result.passed]
            dataset_results.extend(record_results[(dataset, record.row_number)])
            if any(result.severity in {"error", "fatal"} and result.quarantinable for result in failures):
                quarantined_records.append(record)
            else:
                valid_records.append(record)
        outputs[dataset] = DatasetValidationOutput(
            dataset=dataset,
            source_count=len(raw_records[dataset]),
            valid_records=valid_records,
            quarantined_records=quarantined_records,
            results=sorted(dataset_results, key=_result_sort_key),
        )
    return outputs, sorted(dataset_level_results, key=_result_sort_key)


def severity_counts(
    outputs: dict[str, DatasetValidationOutput], dataset_results: list[ValidationResult]
) -> dict[str, int]:
    """Aggregate failed validation result severities."""
    counts: Counter[str] = Counter({"info": 0, "warning": 0, "error": 0, "fatal": 0})
    for result in dataset_results:
        if not result.passed:
            counts[result.severity] += 1
    for output in outputs.values():
        for result in output.results:
            if not result.passed:
                counts[result.severity] += 1
    return dict(counts)


def overall_status(counts: dict[str, int], config: ValidationConfig) -> str:
    """Calculate validation run status from severity thresholds."""
    if counts.get("fatal", 0) > config.settings.max_fatal_count:
        return "failed"
    if config.settings.fail_on_error and counts.get("error", 0) > config.settings.max_error_count:
        return "failed"
    if config.settings.fail_on_warning and counts.get("warning", 0) > config.settings.max_warning_count:
        return "failed"
    return "passed"


def _manifest_results(
    source_run: SourceRun,
    raw_records: dict[str, list[RawRecord]],
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for dataset, source in source_run.datasets.items():
        actual_count = count_source_rows(source.path, source.file_format)
        if config.settings.verify_manifest_row_counts and actual_count != source.row_count:
            results.append(
                _dataset_result(
                    "MAN-ROWCOUNT",
                    dataset,
                    "fatal",
                    "manifest",
                    f"Manifest row count {source.row_count} does not match actual row count {actual_count}.",
                    str(actual_count),
                    "actual row count matches generation manifest",
                    timestamp_utc,
                )
            )
        if not config.settings.allow_empty_datasets and not raw_records[dataset]:
            results.append(
                _dataset_result(
                    "MAN-NONEMPTY",
                    dataset,
                    "error",
                    "manifest",
                    "Dataset is empty.",
                    "0",
                    "dataset contains at least one record",
                    timestamp_utc,
                )
            )
    if not config.settings.verify_source_checksums:
        results.append(
            _dataset_result(
                "MAN-CHECKSUM-WARN",
                "generation-manifest.json",
                "warning",
                "manifest",
                "Source checksum verification is disabled by validation configuration.",
                "disabled",
                "source checksums are verified",
                timestamp_utc,
            )
        )
    return results


def _schema_results(
    contract: DatasetContract,
    records: list[RawRecord],
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    expected = set(contract.field_names)
    for record in records:
        observed = set(record.data)
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        for field_name in missing:
            results.append(
                _result(
                    f"{_prefix(contract.filename)}-001",
                    contract.filename,
                    _blank_record(contract.filename, record.row_number),
                    field_name,
                    "error" if config.settings.missing_column_policy == "reject" else "warning",
                    "schema",
                    f"Missing required column {field_name}.",
                    None,
                    "all required columns are present",
                    timestamp_utc,
                )
            )
        for field_name in unknown:
            results.append(
                _result(
                    f"{_prefix(contract.filename)}-002",
                    contract.filename,
                    _blank_record(contract.filename, record.row_number),
                    field_name,
                    "error" if config.settings.unknown_column_policy == "reject" else "warning",
                    "schema",
                    f"Unknown column {field_name}.",
                    None,
                    "no unknown columns under configured policy",
                    timestamp_utc,
                )
            )
    return results


def _primary_key_results(
    contract: DatasetContract,
    records: list[NormalizedRecord],
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    seen: dict[tuple[str, ...], NormalizedRecord] = {}
    for record in records:
        key = tuple(
            "" if record.data.get(field) is None else str(record.data.get(field)) for field in contract.primary_key
        )
        if any(part == "" for part in key):
            results.append(
                _result(
                    f"{_prefix(contract.filename)}-PK-NULL",
                    contract.filename,
                    record,
                    ",".join(contract.primary_key),
                    "error",
                    "uniqueness",
                    f"Primary key is null or blank: {key}.",
                    "|".join(key),
                    "primary key fields are populated",
                    timestamp_utc,
                )
            )
        if key in seen:
            results.append(
                _result(
                    f"{_prefix(contract.filename)}-PK-DUP",
                    contract.filename,
                    record,
                    ",".join(contract.primary_key),
                    "error",
                    "uniqueness",
                    f"Duplicate primary key: {key}.",
                    "|".join(key),
                    "primary key values are unique",
                    timestamp_utc,
                )
            )
        seen[key] = record
    return results


def _business_results(
    contract: DatasetContract,
    data: dict[str, list[NormalizedRecord]],
    source_run: SourceRun,
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    if contract.filename == "flight_schedule.csv":
        return _flight_schedule_rules(data[contract.filename], source_run, config, timestamp_utc)
    if contract.filename == "passenger_demand.csv":
        return _passenger_demand_rules(data, config, timestamp_utc)
    if contract.filename == "weather_events.csv":
        return _weather_rules(data[contract.filename], config, timestamp_utc)
    if contract.filename == "aircraft_health.jsonl":
        return _aircraft_health_rules(data, source_run, config, timestamp_utc)
    if contract.filename == "crew_operations.csv":
        return _crew_rules(data[contract.filename], timestamp_utc)
    if contract.filename == "delay_history.csv":
        return _delay_rules(data, config, timestamp_utc)
    if contract.filename == "airport_events.jsonl":
        return _airport_event_rules(data[contract.filename], timestamp_utc)
    return []


def _flight_schedule_rules(
    records: list[NormalizedRecord],
    source_run: SourceRun,
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    reference = source_run.manifest["effective_configuration"]["reference"]
    airports = {airport["code"] for airport in reference["airports"]}
    fleet = {aircraft["aircraft_id"]: aircraft for aircraft in reference["fleet"]}
    routes = {route["route_id"]: route for route in reference["routes"]}
    by_aircraft: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        if record.data["origin_airport"] == record.data["destination_airport"]:
            results.append(_failure("FS-003", record, "origin_airport", "origin and destination differ", timestamp_utc))
        dep = _dt(record.data["scheduled_departure_utc"])
        arr = _dt(record.data["scheduled_arrival_utc"])
        if dep is not None and arr is not None and arr <= dep:
            results.append(
                _failure("FS-004", record, "scheduled_arrival_utc", "arrival follows departure", timestamp_utc)
            )
        if record.data["origin_airport"] not in airports or record.data["destination_airport"] not in airports:
            results.append(_failure("FS-005", record, "origin_airport", "airport codes exist", timestamp_utc))
        route = routes.get(str(record.data["route_id"]))
        if route and (route["origin"], route["destination"]) != (
            record.data["origin_airport"],
            record.data["destination_airport"],
        ):
            results.append(
                _failure("FS-006", record, "route_id", "route agrees with origin/destination", timestamp_utc)
            )
        aircraft = fleet.get(str(record.data["aircraft_id"]))
        if aircraft and aircraft["aircraft_type"] != record.data["aircraft_type"]:
            results.append(
                _failure("FS-007", record, "aircraft_type", "aircraft type agrees with fleet", timestamp_utc)
            )
        if aircraft:
            capacity = source_run.manifest["effective_configuration"]["reference"]["aircraft_types"][
                aircraft["aircraft_type"]
            ]
            if int(record.data["seat_capacity"] or 0) != int(capacity["seat_capacity"]):
                results.append(
                    _failure("FS-008", record, "seat_capacity", "seat capacity agrees with fleet type", timestamp_utc)
                )
        if dep is not None and arr is not None:
            block = (arr - dep).total_seconds() / 60
            if (
                abs(block - float(record.data["scheduled_block_minutes"] or 0))
                > config.settings.timestamp_overlap_tolerance_minutes
            ):
                results.append(
                    _warning(
                        "FS-009",
                        record,
                        "scheduled_block_minutes",
                        "block minutes agree with timestamps",
                        timestamp_utc,
                    )
                )
        if record.data.get("aircraft_id") is not None:
            by_aircraft[str(record.data["aircraft_id"])].append(record)
    for aircraft_records in by_aircraft.values():
        ordered = sorted(aircraft_records, key=lambda item: str(item.data["scheduled_departure_utc"]))
        previous_arrival: datetime | None = None
        for record in ordered:
            departure = _dt(record.data["scheduled_departure_utc"])
            arrival = _dt(record.data["scheduled_arrival_utc"])
            if previous_arrival and departure and departure < previous_arrival:
                results.append(
                    _failure("FS-010", record, "aircraft_id", "aircraft flights do not overlap", timestamp_utc)
                )
            if arrival is not None:
                previous_arrival = arrival
    return results


def _passenger_demand_rules(
    data: dict[str, list[NormalizedRecord]],
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    flights = {str(row.data["flight_id"]): row for row in data["flight_schedule.csv"]}
    by_flight = _group_by(data["passenger_demand.csv"], "flight_id")
    for record in data["passenger_demand.csv"]:
        flight = flights.get(str(record.data["flight_id"]))
        if flight:
            if record.data["route_id"] != flight.data["route_id"]:
                results.append(_failure("PD-003", record, "route_id", "route agrees with linked flight", timestamp_utc))
            if record.data["seat_capacity"] != flight.data["seat_capacity"]:
                results.append(
                    _failure("PD-004", record, "seat_capacity", "capacity agrees with linked flight", timestamp_utc)
                )
            departure = _dt(flight.data["scheduled_departure_utc"])
            obs = _date(record.data["observation_date"])
            days = record.data["days_before_departure"]
            if departure and obs and obs > departure.date():
                results.append(
                    _failure("PD-005", record, "observation_date", "observation is not after departure", timestamp_utc)
                )
            if departure and obs and isinstance(days, int) and (departure.date() - obs).days != days:
                results.append(
                    _failure(
                        "PD-006",
                        record,
                        "days_before_departure",
                        "days_before_departure agrees with dates",
                        timestamp_utc,
                    )
                )
        booked = int(record.data["booked_passengers"] or 0)
        expected = int(record.data["expected_final_passengers"] or 0)
        capacity = int(record.data["seat_capacity"] or 1)
        if booked > expected:
            results.append(
                _failure("PD-007", record, "booked_passengers", "booked <= expected final passengers", timestamp_utc)
            )
        if expected > int(capacity * config.settings.controlled_overbooking_tolerance):
            results.append(
                _failure(
                    "PD-008", record, "expected_final_passengers", "controlled overbooking tolerance", timestamp_utc
                )
            )
        if abs(float(record.data["load_factor"] or 0) - round(expected / capacity, 4)) > 0.0001:
            results.append(
                _failure("PD-009", record, "load_factor", "load factor equals expected/capacity", timestamp_utc)
            )
        if float(record.data["booking_velocity"] or 0) > config.settings.booking_velocity_max:
            results.append(
                _warning(
                    "PD-010", record, "booking_velocity", "booking velocity is below warning ceiling", timestamp_utc
                )
            )
    for records in by_flight.values():
        ordered = sorted(records, key=lambda item: int(item.data["days_before_departure"] or 0), reverse=True)
        previous = -1
        for record in ordered:
            booked = int(record.data["booked_passengers"] or 0)
            cancellations = int(record.data["cancellations_to_date"] or 0)
            if previous > booked + cancellations + 5:
                results.append(
                    _warning(
                        "PD-011",
                        record,
                        "booked_passengers",
                        "booking curve does not materially decrease",
                        timestamp_utc,
                    )
                )
            previous = booked
    return results


def _weather_rules(
    records: list[NormalizedRecord], config: ValidationConfig, timestamp_utc: str
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for record in records:
        start = _dt(record.data["event_start_utc"])
        end = _dt(record.data["event_end_utc"])
        if start and end and end <= start:
            results.append(
                _failure("WE-002", record, "event_end_utc", "weather event end follows start", timestamp_utc)
            )
        if float(record.data["wind_gust_knots"] or 0) + 2 < float(record.data["wind_speed_knots"] or 0):
            results.append(
                _warning(
                    "WE-006", record, "wind_gust_knots", "gust is not materially below sustained wind", timestamp_utc
                )
            )
        temp = float(record.data["temperature_c"] or 0)
        if temp < config.settings.temperature_min_c or temp > config.settings.temperature_max_c:
            results.append(
                _failure(
                    "WE-008", record, "temperature_c", "temperature remains within synthetic bounds", timestamp_utc
                )
            )
    return results


def _aircraft_health_rules(
    data: dict[str, list[NormalizedRecord]],
    source_run: SourceRun,
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    flights = {str(row.data["flight_id"]): row for row in data["flight_schedule.csv"]}
    fleet = {
        aircraft["aircraft_id"]: aircraft
        for aircraft in source_run.manifest["effective_configuration"]["reference"]["fleet"]
    }
    ranges = source_run.manifest["effective_configuration"]["reference"]["sensor_ranges"]
    tolerance = config.settings.timestamp_overlap_tolerance_minutes
    for record in data["aircraft_health.jsonl"]:
        aircraft = fleet.get(str(record.data["aircraft_id"]))
        if aircraft and aircraft["aircraft_type"] != record.data["aircraft_type"]:
            results.append(
                _failure("AH-003", record, "aircraft_type", "aircraft type agrees with fleet", timestamp_utc)
            )
        flight = flights.get(str(record.data["flight_id"]))
        event_time = _dt(record.data["event_timestamp_utc"])
        if flight and event_time:
            departure = _dt(flight.data["scheduled_departure_utc"])
            arrival = _dt(flight.data["scheduled_arrival_utc"])
            if (
                departure
                and arrival
                and not (departure.timestamp() - 7200 <= event_time.timestamp() <= arrival.timestamp() + tolerance * 60)
            ):
                results.append(
                    _failure("AH-004", record, "event_timestamp_utc", "telemetry is near linked flight", timestamp_utc)
                )
            if flight.data["aircraft_id"] != record.data["aircraft_id"]:
                results.append(
                    _failure(
                        "AH-005",
                        record,
                        "aircraft_id",
                        "telemetry aircraft agrees with flight assignment",
                        timestamp_utc,
                    )
                )
        aircraft_type = str(record.data["aircraft_type"])
        if aircraft_type in ranges:
            for sensor, bounds in ranges[aircraft_type].items():
                value = float(record.data[sensor] or 0)
                low = float(bounds[0]) * 0.8
                high = float(bounds[1]) * 1.15
                if value < low or value > high:
                    results.append(
                        _failure(
                            "AH-006", record, sensor, "sensor remains within configured hard bounds", timestamp_utc
                        )
                    )
        if (
            record.data["health_status"] == "review"
            and not record.data["fault_code"]
            and float(record.data["maintenance_risk_score"] or 0) >= 70
        ):
            results.append(
                _warning(
                    "AH-007", record, "fault_code", "review states include supporting fault context", timestamp_utc
                )
            )
    return results


def _crew_rules(records: list[NormalizedRecord], timestamp_utc: str) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for record in records:
        start = _dt(record.data["duty_start_utc"])
        end = _dt(record.data["duty_end_utc"])
        if start and end:
            if end <= start:
                results.append(_failure("CR-002", record, "duty_end_utc", "duty end follows duty start", timestamp_utc))
            minutes = int((end - start).total_seconds() // 60)
            if abs(minutes - int(record.data["duty_minutes"] or 0)) > 1:
                results.append(
                    _failure("CR-003", record, "duty_minutes", "duty minutes agree with timestamps", timestamp_utc)
                )
        if bool(record.data["crew_disruption_flag"]) and not record.data["crew_disruption_reason"]:
            results.append(
                _failure(
                    "CR-004",
                    record,
                    "crew_disruption_reason",
                    "disruption reason is present when disrupted",
                    timestamp_utc,
                )
            )
        if not bool(record.data["crew_disruption_flag"]) and record.data["crew_disruption_reason"]:
            results.append(
                _warning(
                    "CR-005", record, "crew_disruption_reason", "reason is blank when not disrupted", timestamp_utc
                )
            )
    return results


def _delay_rules(
    data: dict[str, list[NormalizedRecord]],
    config: ValidationConfig,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    flights = {str(row.data["flight_id"]): row for row in data["flight_schedule.csv"]}
    airports = {str(row.data["origin_airport"]) for row in data["flight_schedule.csv"]} | {
        str(row.data["destination_airport"]) for row in data["flight_schedule.csv"]
    }
    for record in data["delay_history.csv"]:
        flight = flights.get(str(record.data["flight_id"]))
        cancelled = bool(record.data["cancelled_flag"])
        diverted = bool(record.data["diverted_flag"])
        actual_departure = _dt(record.data["actual_departure_utc"])
        actual_arrival = _dt(record.data["actual_arrival_utc"])
        if cancelled and (actual_departure is not None or actual_arrival is not None):
            results.append(
                _failure("DH-002", record, "cancelled_flag", "cancelled flights have no actual times", timestamp_utc)
            )
        if not cancelled and (actual_departure is None or actual_arrival is None):
            results.append(
                _failure(
                    "DH-003", record, "actual_departure_utc", "non-cancelled flights have actual times", timestamp_utc
                )
            )
        if actual_departure and actual_arrival and actual_arrival <= actual_departure:
            results.append(
                _failure(
                    "DH-004", record, "actual_arrival_utc", "actual arrival follows actual departure", timestamp_utc
                )
            )
        if flight and actual_departure:
            scheduled_departure = _dt(flight.data["scheduled_departure_utc"])
            if scheduled_departure:
                observed = round((actual_departure - scheduled_departure).total_seconds() / 60)
                if abs(observed - int(record.data["departure_delay_minutes"] or 0)) > 1:
                    results.append(
                        _failure(
                            "DH-005",
                            record,
                            "departure_delay_minutes",
                            "departure delay agrees with actual departure",
                            timestamp_utc,
                        )
                    )
                if observed < -config.settings.early_departure_allowance_minutes:
                    results.append(
                        _failure(
                            "DH-010",
                            record,
                            "departure_delay_minutes",
                            "early operation within configured allowance",
                            timestamp_utc,
                        )
                    )
        if _delay_category(int(record.data["departure_delay_minutes"] or 0)) != record.data["delay_category"]:
            results.append(
                _failure("DH-007", record, "delay_category", "delay category agrees with delay minutes", timestamp_utc)
            )
        diversion = record.data["diversion_airport"]
        if diverted and not diversion:
            results.append(
                _failure(
                    "DH-008", record, "diversion_airport", "diverted flights have diversion airport", timestamp_utc
                )
            )
        if not diverted and diversion:
            results.append(
                _failure(
                    "DH-009",
                    record,
                    "diversion_airport",
                    "non-diverted flights do not have diversion airport",
                    timestamp_utc,
                )
            )
        if diversion and str(diversion) not in airports:
            results.append(_failure("DH-011", record, "diversion_airport", "diversion airport is valid", timestamp_utc))
    return results


def _airport_event_rules(records: list[NormalizedRecord], timestamp_utc: str) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    for record in records:
        start = _dt(record.data["event_start_utc"])
        end = _dt(record.data["event_end_utc"])
        if start and end and end <= start:
            results.append(
                _failure("AE-002", record, "event_end_utc", "airport event end follows start", timestamp_utc)
            )
        severity = int(record.data["severity"] or 0)
        reduction = int(record.data["capacity_reduction_percent"] or 0)
        delay = int(record.data["estimated_delay_minutes"] or 0)
        if reduction < severity * 4 or delay < severity * 4:
            results.append(_warning("AE-003", record, "severity", "severity broadly agrees with impact", timestamp_utc))
        notes = str(record.data["operational_notes"] or "")
        if "Synthetic" not in notes:
            results.append(
                _failure(
                    "AE-004",
                    record,
                    "operational_notes",
                    "notes remain templated synthetic descriptions",
                    timestamp_utc,
                )
            )
    return results


def _relationship_results(
    data: dict[str, list[NormalizedRecord]],
    source_run: SourceRun,
    timestamp_utc: str,
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    reference = source_run.manifest["effective_configuration"]["reference"]
    airports = {airport["code"] for airport in reference["airports"]}
    fleet = {aircraft["aircraft_id"] for aircraft in reference["fleet"]}
    routes = {route["route_id"] for route in reference["routes"]}
    flight_ids = {str(record.data["flight_id"]) for record in data["flight_schedule.csv"]}
    for dataset, field, allowed, rule_id in (
        ("flight_schedule.csv", "origin_airport", airports, "REL-001"),
        ("flight_schedule.csv", "destination_airport", airports, "REL-002"),
        ("flight_schedule.csv", "aircraft_id", fleet, "REL-003"),
        ("flight_schedule.csv", "route_id", routes, "REL-004"),
        ("weather_events.csv", "airport_code", airports, "REL-005"),
        ("airport_events.jsonl", "airport_code", airports, "REL-006"),
        ("aircraft_health.jsonl", "aircraft_id", fleet, "REL-007"),
    ):
        for record in data[dataset]:
            if record.data[field] not in allowed:
                results.append(_failure(rule_id, record, field, "foreign key resolves", timestamp_utc))
    for dataset, rule_id in (
        ("passenger_demand.csv", "REL-010"),
        ("crew_operations.csv", "REL-011"),
        ("delay_history.csv", "REL-012"),
        ("aircraft_health.jsonl", "REL-013"),
    ):
        for record in data[dataset]:
            if str(record.data["flight_id"]) not in flight_ids:
                results.append(_failure(rule_id, record, "flight_id", "flight foreign key resolves", timestamp_utc))
    for dataset, rule_id in (
        ("passenger_demand.csv", "REL-020"),
        ("crew_operations.csv", "REL-021"),
        ("delay_history.csv", "REL-022"),
        ("aircraft_health.jsonl", "REL-023"),
    ):
        seen = {str(record.data["flight_id"]) for record in data[dataset]}
        missing = sorted(flight_ids - seen)
        for flight_id in missing:
            results.append(
                _dataset_result(
                    rule_id,
                    dataset,
                    "error",
                    "integrity",
                    f"Missing required record for flight {flight_id}.",
                    flight_id,
                    "every flight has required linked records",
                    timestamp_utc,
                )
            )
    return results


def _result(
    rule_id: str,
    dataset: str,
    record: NormalizedRecord,
    field_name: str | None,
    severity: str,
    category: str,
    message: str,
    observed_value: str | None,
    expected_condition: str,
    timestamp_utc: str,
) -> ValidationResult:
    return ValidationResult(
        rule_id=rule_id,
        dataset=dataset,
        record_identifier=_record_identifier(record),
        field_name=field_name,
        severity=cast(Severity, severity),
        category=category,
        message=message,
        observed_value=observed_value,
        expected_condition=expected_condition,
        source_file=dataset,
        row_number=record.row_number,
        passed=False,
        quarantinable=True,
        timestamp_generated_utc=timestamp_utc,
    )


def _dataset_result(
    rule_id: str,
    dataset: str,
    severity: str,
    category: str,
    message: str,
    observed_value: str | None,
    expected_condition: str,
    timestamp_utc: str,
) -> ValidationResult:
    return ValidationResult(
        rule_id=rule_id,
        dataset=dataset,
        record_identifier=None,
        field_name=None,
        severity=cast(Severity, severity),
        category=category,
        message=message,
        observed_value=observed_value,
        expected_condition=expected_condition,
        source_file=dataset,
        row_number=None,
        passed=False,
        quarantinable=False,
        timestamp_generated_utc=timestamp_utc,
    )


def _failure(
    rule_id: str, record: NormalizedRecord, field_name: str, expected: str, timestamp_utc: str
) -> ValidationResult:
    return _result(
        rule_id,
        record.dataset,
        record,
        field_name,
        "error",
        "business_rule" if not rule_id.startswith("REL") else "integrity",
        f"{field_name} failed rule {rule_id}.",
        None if record.data.get(field_name) is None else str(record.data.get(field_name)),
        expected,
        timestamp_utc,
    )


def _warning(
    rule_id: str, record: NormalizedRecord, field_name: str, expected: str, timestamp_utc: str
) -> ValidationResult:
    return _result(
        rule_id,
        record.dataset,
        record,
        field_name,
        "warning",
        "business_rule",
        f"{field_name} triggered warning rule {rule_id}.",
        None if record.data.get(field_name) is None else str(record.data.get(field_name)),
        expected,
        timestamp_utc,
    )


def _blank_record(dataset: str, row_number: int) -> NormalizedRecord:
    return NormalizedRecord(dataset=dataset, row_number=row_number, data={})


def _record_identifier(record: NormalizedRecord) -> str | None:
    for field in ("flight_id", "weather_event_id", "telemetry_id", "crew_assignment_id", "airport_event_id"):
        value = record.data.get(field)
        if value:
            return str(value)
    return None


def _prefix(dataset: str) -> str:
    return {
        "flight_schedule.csv": "FS",
        "passenger_demand.csv": "PD",
        "weather_events.csv": "WE",
        "aircraft_health.jsonl": "AH",
        "crew_operations.csv": "CR",
        "delay_history.csv": "DH",
        "airport_events.jsonl": "AE",
    }[dataset]


def _dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value).date()


def _group_by(records: list[NormalizedRecord], field: str) -> dict[str, list[NormalizedRecord]]:
    grouped: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        grouped[str(record.data[field])].append(record)
    return grouped


def _delay_category(minutes: int) -> str:
    if minutes < 0:
        return "early"
    if minutes < 15:
        return "on_time"
    if minutes < 45:
        return "minor"
    if minutes < 90:
        return "moderate"
    return "major"


def _result_sort_key(result: ValidationResult) -> tuple[str, int, str, str]:
    return (
        result.dataset,
        -1 if result.row_number is None else result.row_number,
        result.rule_id,
        result.field_name or "",
    )
