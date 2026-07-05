PYTHON ?= python3

.PHONY: install format lint typecheck test docs-check yaml-check validate generate-data-ci validate-data-ci forecast-passenger-demand-ci test-data-generation test-ingestion-validation test-passenger-forecasting describe-validation-ci describe-passenger-forecast-ci quality clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

docs-check:
	$(PYTHON) -m pymarkdown --config .pymarkdown.yml scan README.md CONTRIBUTING.md SECURITY.md docs diagrams

yaml-check:
	$(PYTHON) -m yamllint .

validate:
	$(PYTHON) -m airline_operations_intelligence.cli validate-repository

generate-data-ci:
	$(PYTHON) -m airline_operations_intelligence.cli generate-data --config configs/data_generation_ci.yaml --run-id ci-quality --overwrite

validate-data-ci: generate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli validate-data --source-run-dir data/raw/ci-quality --config configs/validation_ci.yaml --validation-run-id ci-quality --overwrite

forecast-passenger-demand-ci: validate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli forecast-passenger-demand --validation-report-dir reports/validation/ci-quality --config configs/passenger_forecasting_ci.yaml --forecast-run-id ci-quality --overwrite

test-data-generation:
	$(PYTHON) -m pytest tests/integration/test_data_generation.py

test-ingestion-validation:
	$(PYTHON) -m pytest tests/unit/test_validation_config.py tests/unit/test_ingestion_validation.py tests/integration/test_validation_pipeline.py

test-passenger-forecasting:
	$(PYTHON) -m pytest tests/unit/test_passenger_forecasting_config.py tests/unit/test_passenger_forecasting.py tests/integration/test_passenger_forecasting_pipeline.py

describe-validation-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-validation --report-dir reports/validation/ci-quality

describe-passenger-forecast-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-passenger-forecast --forecast-report-dir reports/passenger_forecasting/ci-quality

quality: lint typecheck test docs-check yaml-check validate generate-data-ci validate-data-ci forecast-passenger-demand-ci

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache build dist *.egg-info data/raw/ci-quality data/raw/.ci-quality.tmp data/interim/ci-quality data/interim/.ci-quality.tmp data/processed/ci-quality data/processed/.ci-quality.tmp reports/validation/ci-quality reports/validation/.ci-quality.tmp outputs/passenger_forecasting/ci-quality outputs/passenger_forecasting/.ci-quality.tmp outputs/models/passenger_forecasting/ci-quality outputs/models/passenger_forecasting/.ci-quality.tmp reports/passenger_forecasting/ci-quality reports/passenger_forecasting/.ci-quality.tmp
