from datetime import datetime

from airline_operations_intelligence.data_generation.config import load_generation_config
from airline_operations_intelligence.data_generation.delays import delay_category
from airline_operations_intelligence.data_generation.demand import generate_passenger_demand
from airline_operations_intelligence.data_generation.randomness import make_rng, stable_id
from airline_operations_intelligence.data_generation.schedule import generate_schedule
from airline_operations_intelligence.data_generation.weather import generate_weather_events


def test_stable_id_and_seeded_rng_are_deterministic() -> None:
    assert stable_id("X", "a", 1) == stable_id("X", "a", 1)
    assert make_rng(42, "domain").random() == make_rng(42, "domain").random()


def test_schedule_timestamps_and_route_consistency() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")
    schedule = generate_schedule(config, make_rng(config.settings.seed, "schedule-test"))
    route_map = config.route_map

    assert len(schedule.records) == config.settings.number_of_days * config.settings.flights_per_day
    for row in schedule.records:
        departure = datetime.fromisoformat(str(row["scheduled_departure_utc"]).replace("Z", "+00:00"))
        arrival = datetime.fromisoformat(str(row["scheduled_arrival_utc"]).replace("Z", "+00:00"))
        assert arrival > departure
        route = route_map[str(row["route_id"])]
        assert row["origin_airport"] == route["origin"]
        assert row["destination_airport"] == route["destination"]


def test_passenger_demand_bounds() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")
    schedule = generate_schedule(config, make_rng(config.settings.seed, "schedule-test"))
    demand = generate_passenger_demand(config, schedule, make_rng(config.settings.seed, "demand-test"))

    for row in demand.records:
        assert int(row["booked_passengers"]) <= int(row["expected_final_passengers"])
        assert float(row["load_factor"]) == round(
            int(row["expected_final_passengers"]) / int(row["seat_capacity"]),
            4,
        )


def test_weather_severity_influences_impact_score() -> None:
    config = load_generation_config("configs/data_generation_ci.yaml")
    weather = generate_weather_events(config, make_rng(config.settings.seed, "weather-test"))

    assert weather.records
    for row in weather.records:
        assert 1 <= int(row["severity"]) <= 5
        assert float(row["operational_impact_score"]) >= int(row["severity"]) * 18


def test_delay_category_thresholds() -> None:
    assert delay_category(-1) == "early"
    assert delay_category(0) == "on_time"
    assert delay_category(20) == "minor"
    assert delay_category(60) == "moderate"
    assert delay_category(100) == "major"
