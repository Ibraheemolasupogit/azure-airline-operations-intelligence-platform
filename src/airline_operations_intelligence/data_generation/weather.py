"""Synthetic airport weather generation."""

from __future__ import annotations

import random
from datetime import UTC, datetime, time, timedelta

from airline_operations_intelligence.data_generation.config import GenerationConfig
from airline_operations_intelligence.data_generation.models import Dataset, Record
from airline_operations_intelligence.data_generation.randomness import stable_id


def generate_weather_events(config: GenerationConfig, rng: random.Random) -> Dataset:
    """Generate airport weather observations and event windows."""
    records: list[Record] = []
    weather_types = sorted(config.weather_event_probabilities)
    for day_offset in range(config.settings.number_of_days):
        day = config.settings.start_date + timedelta(days=day_offset)
        seasonal_factor = _seasonal_factor(day.month)
        for airport in sorted(config.airports, key=lambda item: str(item["code"])):
            airport_code = str(airport["code"])
            for weather_type in weather_types:
                probability = config.weather_event_probabilities[weather_type] * seasonal_factor
                if rng.random() > min(probability, 0.95):
                    continue
                start_hour = rng.randint(4, 20)
                duration = rng.randint(1, 5)
                start = datetime.combine(day, time(start_hour, rng.choice([0, 15, 30, 45])), tzinfo=UTC)
                end = start + timedelta(hours=duration)
                severity = _severity(weather_type, rng)
                wind_speed = round(rng.uniform(8, 24) + severity * 7, 1)
                gust = round(wind_speed + rng.uniform(3, 18), 1)
                visibility = max(250, int(8000 - severity * rng.randint(900, 1800)))
                precipitation = round(max(0.0, severity * rng.uniform(0.3, 5.5)), 1)
                impact = min(100, round(severity * 18 + max(0, wind_speed - 25) * 1.5 + precipitation * 2, 2))
                records.append(
                    {
                        "weather_event_id": stable_id("WX", airport_code, start.isoformat(), weather_type),
                        "airport_code": airport_code,
                        "event_start_utc": start.isoformat().replace("+00:00", "Z"),
                        "event_end_utc": end.isoformat().replace("+00:00", "Z"),
                        "weather_type": weather_type,
                        "severity": severity,
                        "temperature_c": round(rng.uniform(-4, 30), 1),
                        "wind_speed_knots": wind_speed,
                        "wind_gust_knots": gust,
                        "visibility_metres": visibility,
                        "precipitation_mm": precipitation,
                        "operational_impact_score": impact,
                    }
                )
    return Dataset(
        filename="weather_events.csv",
        file_format="csv",
        grain="one row per airport weather observation or event window",
        primary_key="weather_event_id",
        foreign_keys={"airport_code": "airports.code"},
        records=records,
        time_field="event_start_utc",
    )


def _severity(weather_type: str, rng: random.Random) -> int:
    base = {"clear_wind": 1, "rain": 2, "thunderstorm": 4, "fog": 3, "snow": 4}.get(weather_type, 2)
    return min(5, max(1, base + rng.choice([-1, 0, 0, 1])))


def _seasonal_factor(month: int) -> float:
    if month in {12, 1, 2}:
        return 1.35
    if month in {6, 7, 8}:
        return 1.1
    return 1.0
