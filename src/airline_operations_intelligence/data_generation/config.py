"""Configuration parsing for deterministic synthetic data generation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from airline_operations_intelligence.common.exceptions import GenerationConfigurationError

DEFAULT_GENERATION_CONFIG_PATH = Path("configs/data_generation.yaml")

SUPPORTED_AIRCRAFT_TYPES = {"A320", "A321", "B737-800", "B787-9", "E190"}


@dataclass(frozen=True)
class GenerationSettings:
    """Validated generation run settings."""

    profile: str
    seed: int
    start_date: date
    number_of_days: int
    flights_per_day: int
    output_root: Path
    overwrite: bool
    anomaly_rate: float
    demand_observation_days: tuple[int, ...]
    max_overbooking_ratio: float


@dataclass(frozen=True)
class GenerationConfig:
    """Validated synthetic aviation data-generation configuration."""

    settings: GenerationSettings
    airports: tuple[dict[str, Any], ...]
    routes: tuple[dict[str, Any], ...]
    aircraft_types: dict[str, dict[str, Any]]
    fleet: tuple[dict[str, Any], ...]
    carriers: tuple[str, ...]
    crew_bases: tuple[str, ...]
    weather_event_probabilities: dict[str, float]
    airport_event_probabilities: dict[str, float]
    demand_seasonality: dict[str, float]
    delay_cause_probabilities: dict[str, float]
    sensor_ranges: dict[str, dict[str, tuple[float, float]]]
    maintenance_risk: dict[str, float]

    @property
    def airport_codes(self) -> set[str]:
        """Return configured airport codes."""
        return {str(airport["code"]) for airport in self.airports}

    @property
    def route_map(self) -> dict[str, dict[str, Any]]:
        """Return routes keyed by route ID."""
        return {str(route["route_id"]): route for route in self.routes}

    @property
    def fleet_map(self) -> dict[str, dict[str, Any]]:
        """Return fleet records keyed by aircraft ID."""
        return {str(aircraft["aircraft_id"]): aircraft for aircraft in self.fleet}

    def effective_configuration(self) -> dict[str, Any]:
        """Return a deterministic JSON-serialisable configuration snapshot."""
        return {
            "generation": {
                "profile": self.settings.profile,
                "seed": self.settings.seed,
                "start_date": self.settings.start_date.isoformat(),
                "number_of_days": self.settings.number_of_days,
                "flights_per_day": self.settings.flights_per_day,
                "output_root": self.settings.output_root.as_posix(),
                "overwrite": self.settings.overwrite,
                "anomaly_rate": self.settings.anomaly_rate,
                "demand_observation_days": list(self.settings.demand_observation_days),
                "max_overbooking_ratio": self.settings.max_overbooking_ratio,
            },
            "reference": {
                "airports": list(self.airports),
                "routes": list(self.routes),
                "aircraft_types": self.aircraft_types,
                "fleet": list(self.fleet),
                "carriers": list(self.carriers),
                "crew_bases": list(self.crew_bases),
                "weather_event_probabilities": self.weather_event_probabilities,
                "airport_event_probabilities": self.airport_event_probabilities,
                "demand_seasonality": self.demand_seasonality,
                "delay_cause_probabilities": self.delay_cause_probabilities,
                "sensor_ranges": self.sensor_ranges,
                "maintenance_risk": self.maintenance_risk,
            },
        }

    def fingerprint(self) -> str:
        """Return a stable fingerprint of the effective configuration."""
        payload = json.dumps(self.effective_configuration(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_generation_config(path: Path | str) -> GenerationConfig:
    """Load and validate generation configuration from YAML."""
    config_path = Path(path)
    if not config_path.exists():
        raise GenerationConfigurationError(f"Generation configuration file not found: {config_path}")
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GenerationConfigurationError(f"Generation configuration is not valid YAML: {config_path}") from exc
    if not isinstance(raw, dict):
        raise GenerationConfigurationError("Generation configuration root must be a mapping.")
    return parse_generation_config(raw)


def parse_generation_config(raw: dict[str, Any]) -> GenerationConfig:
    """Validate a raw generation configuration mapping."""
    generation = _require_mapping(raw, "generation")
    reference = _require_mapping(raw, "reference")
    settings = GenerationSettings(
        profile=_str(generation.get("profile", "development"), "generation.profile"),
        seed=_int(generation.get("seed"), "generation.seed"),
        start_date=_date(generation.get("start_date"), "generation.start_date"),
        number_of_days=_positive_int(generation.get("number_of_days"), "generation.number_of_days"),
        flights_per_day=_positive_int(generation.get("flights_per_day"), "generation.flights_per_day"),
        output_root=_output_root(generation.get("output_root", "data/raw")),
        overwrite=_bool(generation.get("overwrite", False), "generation.overwrite"),
        anomaly_rate=_probability(generation.get("anomaly_rate", 0.01), "generation.anomaly_rate"),
        demand_observation_days=tuple(
            sorted(
                {
                    _non_negative_int(value, "generation.demand_observation_days")
                    for value in generation.get("demand_observation_days", [60, 30, 14, 7, 1])
                },
                reverse=True,
            )
        ),
        max_overbooking_ratio=_ratio(
            generation.get("max_overbooking_ratio", 1.05),
            "generation.max_overbooking_ratio",
            minimum=1.0,
            maximum=1.2,
        ),
    )
    airports = tuple(_list_of_mappings(reference, "airports"))
    routes = tuple(_list_of_mappings(reference, "routes"))
    aircraft_types = _require_mapping(reference, "aircraft_types")
    fleet = tuple(_list_of_mappings(reference, "fleet"))
    carriers = tuple(_str(value, "reference.carriers") for value in _require_list(reference, "carriers"))
    crew_bases = tuple(_str(value, "reference.crew_bases") for value in _require_list(reference, "crew_bases"))
    weather_probs = _probability_mapping(reference, "weather_event_probabilities")
    airport_probs = _probability_mapping(reference, "airport_event_probabilities")
    demand_seasonality = {
        key: _positive_float(value, f"reference.demand_seasonality.{key}")
        for key, value in _require_mapping(reference, "demand_seasonality").items()
    }
    delay_probs = _probability_mapping(reference, "delay_cause_probabilities")
    sensor_ranges = _sensor_ranges(reference)
    maintenance_risk = {
        key: _positive_float(value, f"reference.maintenance_risk.{key}")
        for key, value in _require_mapping(reference, "maintenance_risk").items()
    }
    config = GenerationConfig(
        settings=settings,
        airports=airports,
        routes=routes,
        aircraft_types={str(key): value for key, value in aircraft_types.items()},
        fleet=fleet,
        carriers=carriers,
        crew_bases=crew_bases,
        weather_event_probabilities=weather_probs,
        airport_event_probabilities=airport_probs,
        demand_seasonality=demand_seasonality,
        delay_cause_probabilities=delay_probs,
        sensor_ranges=sensor_ranges,
        maintenance_risk=maintenance_risk,
    )
    _validate_dimensions(config)
    return config


def build_run_id(config: GenerationConfig, explicit_run_id: str | None = None) -> str:
    """Build a filesystem-safe run ID."""
    if explicit_run_id:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", explicit_run_id):
            raise GenerationConfigurationError("run_id may contain only letters, numbers, '.', '_', '-'.")
        return explicit_run_id
    seed = config.settings.seed
    start = config.settings.start_date.isoformat().replace("-", "")
    fingerprint = config.fingerprint()[:10]
    profile = re.sub(r"[^A-Za-z0-9._-]+", "-", config.settings.profile).strip("-").lower()
    return f"{profile}-{start}-{config.settings.number_of_days}d-seed{seed}-{fingerprint}"


def with_overrides(
    config: GenerationConfig,
    *,
    seed: int | None = None,
    output_root: Path | None = None,
    overwrite: bool | None = None,
) -> GenerationConfig:
    """Return a copy of config with explicit CLI overrides applied."""
    settings = config.settings
    replaced = GenerationSettings(
        profile=settings.profile,
        seed=settings.seed if seed is None else seed,
        start_date=settings.start_date,
        number_of_days=settings.number_of_days,
        flights_per_day=settings.flights_per_day,
        output_root=settings.output_root if output_root is None else _output_root(output_root),
        overwrite=settings.overwrite if overwrite is None else overwrite,
        anomaly_rate=settings.anomaly_rate,
        demand_observation_days=settings.demand_observation_days,
        max_overbooking_ratio=settings.max_overbooking_ratio,
    )
    return GenerationConfig(
        settings=replaced,
        airports=config.airports,
        routes=config.routes,
        aircraft_types=config.aircraft_types,
        fleet=config.fleet,
        carriers=config.carriers,
        crew_bases=config.crew_bases,
        weather_event_probabilities=config.weather_event_probabilities,
        airport_event_probabilities=config.airport_event_probabilities,
        demand_seasonality=config.demand_seasonality,
        delay_cause_probabilities=config.delay_cause_probabilities,
        sensor_ranges=config.sensor_ranges,
        maintenance_risk=config.maintenance_risk,
    )


def _validate_dimensions(config: GenerationConfig) -> None:
    airport_codes = [str(airport.get("code", "")) for airport in config.airports]
    _reject_duplicates(airport_codes, "airport codes")
    if len(airport_codes) < 2:
        raise GenerationConfigurationError("At least two airports are required.")
    for airport in config.airports:
        code = _str(airport.get("code"), "airport.code")
        if not re.fullmatch(r"[A-Z]{3}", code):
            raise GenerationConfigurationError(f"Airport code must be three uppercase letters: {code}")

    for aircraft_type, metadata in config.aircraft_types.items():
        if aircraft_type not in SUPPORTED_AIRCRAFT_TYPES:
            raise GenerationConfigurationError(f"Unsupported aircraft type: {aircraft_type}")
        capacity = _int(metadata.get("seat_capacity"), f"aircraft_types.{aircraft_type}.seat_capacity")
        if capacity < 30 or capacity > 350:
            raise GenerationConfigurationError(f"Impossible seating capacity for {aircraft_type}: {capacity}")

    aircraft_ids = [str(aircraft.get("aircraft_id", "")) for aircraft in config.fleet]
    _reject_duplicates(aircraft_ids, "aircraft identifiers")
    for aircraft in config.fleet:
        aircraft_type = _str(aircraft.get("aircraft_type"), "fleet.aircraft_type")
        if aircraft_type not in config.aircraft_types:
            raise GenerationConfigurationError(f"Fleet references unknown aircraft type: {aircraft_type}")
        base = _str(aircraft.get("base_airport"), "fleet.base_airport")
        if base not in airport_codes:
            raise GenerationConfigurationError(f"Fleet references unknown base airport: {base}")

    route_ids = [str(route.get("route_id", "")) for route in config.routes]
    _reject_duplicates(route_ids, "route identifiers")
    for route in config.routes:
        origin = _str(route.get("origin"), "route.origin")
        destination = _str(route.get("destination"), "route.destination")
        if origin not in airport_codes or destination not in airport_codes:
            raise GenerationConfigurationError(f"Route {route.get('route_id')} references an unknown airport.")
        if origin == destination:
            raise GenerationConfigurationError(f"Route {route.get('route_id')} has the same origin and destination.")
        _positive_int(route.get("scheduled_block_minutes"), "route.scheduled_block_minutes")
        _positive_float(route.get("popularity"), "route.popularity")


def _require_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise GenerationConfigurationError(f"{key} must be present and must be a mapping.")
    return value


def _require_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise GenerationConfigurationError(f"{key} must be a non-empty list.")
    return value


def _list_of_mappings(raw: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = _require_list(raw, key)
    if not all(isinstance(value, dict) for value in values):
        raise GenerationConfigurationError(f"{key} must contain mappings.")
    return values


def _str(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenerationConfigurationError(f"{key} must be a non-empty string.")
    return value


def _int(value: Any, key: str) -> int:
    if not isinstance(value, int):
        raise GenerationConfigurationError(f"{key} must be an integer.")
    return value


def _positive_int(value: Any, key: str) -> int:
    number = _int(value, key)
    if number <= 0:
        raise GenerationConfigurationError(f"{key} must be positive.")
    return number


def _non_negative_int(value: Any, key: str) -> int:
    number = _int(value, key)
    if number < 0:
        raise GenerationConfigurationError(f"{key} must be non-negative.")
    return number


def _positive_float(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise GenerationConfigurationError(f"{key} must be numeric.")
    number = float(value)
    if number <= 0:
        raise GenerationConfigurationError(f"{key} must be positive.")
    return number


def _bool(value: Any, key: str) -> bool:
    if not isinstance(value, bool):
        raise GenerationConfigurationError(f"{key} must be a boolean.")
    return value


def _date(value: Any, key: str) -> date:
    if not isinstance(value, str):
        raise GenerationConfigurationError(f"{key} must be an ISO date string.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise GenerationConfigurationError(f"{key} must be a valid ISO date.") from exc


def _probability(value: Any, key: str) -> float:
    if not isinstance(value, int | float):
        raise GenerationConfigurationError(f"{key} must be numeric.")
    number = float(value)
    if number < 0 or number > 1:
        raise GenerationConfigurationError(f"{key} must be between 0 and 1.")
    return number


def _ratio(value: Any, key: str, *, minimum: float, maximum: float) -> float:
    if not isinstance(value, int | float):
        raise GenerationConfigurationError(f"{key} must be numeric.")
    number = float(value)
    if number < minimum or number > maximum:
        raise GenerationConfigurationError(f"{key} must be between {minimum} and {maximum}.")
    return number


def _probability_mapping(raw: dict[str, Any], key: str) -> dict[str, float]:
    values = _require_mapping(raw, key)
    return {str(name): _probability(value, f"reference.{key}.{name}") for name, value in values.items()}


def _sensor_ranges(raw: dict[str, Any]) -> dict[str, dict[str, tuple[float, float]]]:
    values = _require_mapping(raw, "sensor_ranges")
    parsed: dict[str, dict[str, tuple[float, float]]] = {}
    for aircraft_type, ranges in values.items():
        if aircraft_type not in SUPPORTED_AIRCRAFT_TYPES:
            raise GenerationConfigurationError(f"Sensor ranges reference unsupported type: {aircraft_type}")
        if not isinstance(ranges, dict):
            raise GenerationConfigurationError(f"sensor_ranges.{aircraft_type} must be a mapping.")
        parsed[str(aircraft_type)] = {}
        for sensor, bounds in ranges.items():
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise GenerationConfigurationError(f"sensor_ranges.{aircraft_type}.{sensor} needs [min, max].")
            low = _positive_float(bounds[0], f"sensor_ranges.{aircraft_type}.{sensor}[0]")
            high = _positive_float(bounds[1], f"sensor_ranges.{aircraft_type}.{sensor}[1]")
            if low >= high:
                raise GenerationConfigurationError(f"sensor range minimum must be below maximum for {sensor}.")
            parsed[str(aircraft_type)][str(sensor)] = (low, high)
    return parsed


def _output_root(value: Any) -> Path:
    output_root = Path(_str(str(value), "generation.output_root"))
    if output_root.is_absolute():
        raise GenerationConfigurationError("generation.output_root must be repository-relative.")
    normalised = Path(*output_root.parts)
    if len(normalised.parts) < 2 or normalised.parts[:2] != ("data", "raw"):
        raise GenerationConfigurationError("generation.output_root must be under data/raw.")
    if ".." in normalised.parts:
        raise GenerationConfigurationError("generation.output_root cannot contain '..'.")
    return normalised


def _reject_duplicates(values: list[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise GenerationConfigurationError(f"Duplicate {label}: {value}")
        seen.add(value)
