PYTHON ?= python3

.PHONY: install format lint typecheck test docs-check yaml-check validate validate-azure-architecture generate-data-ci validate-data-ci forecast-passenger-demand-ci predict-flight-delays-ci analyse-aircraft-health-ci score-disruptions-ci monitor-platform-ci run-operations-assistant-ci build-dashboard-outputs-ci test-data-generation test-ingestion-validation test-passenger-forecasting test-delay-prediction test-maintenance-analytics test-disruption-scoring test-monitoring test-genai-assistant test-dashboard-outputs test-azure-architecture describe-validation-ci describe-passenger-forecast-ci describe-delay-prediction-ci describe-aircraft-health-ci describe-disruption-scoring-ci describe-monitoring-ci describe-operations-assistant-ci describe-dashboard-outputs-ci quality clean

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

validate-azure-architecture:
	$(PYTHON) scripts/validate_azure_architecture.py

generate-data-ci:
	$(PYTHON) -m airline_operations_intelligence.cli generate-data --config configs/data_generation_ci.yaml --run-id ci-quality --overwrite

validate-data-ci: generate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli validate-data --source-run-dir data/raw/ci-quality --config configs/validation_ci.yaml --validation-run-id ci-quality --overwrite

forecast-passenger-demand-ci: validate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli forecast-passenger-demand --validation-report-dir reports/validation/ci-quality --config configs/passenger_forecasting_ci.yaml --forecast-run-id ci-quality --overwrite

predict-flight-delays-ci: validate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli predict-flight-delays --validation-report-dir reports/validation/ci-quality --config configs/delay_prediction_ci.yaml --delay-run-id ci-quality --overwrite

analyse-aircraft-health-ci: validate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli analyse-aircraft-health --validation-report-dir reports/validation/ci-quality --config configs/maintenance_analytics_ci.yaml --maintenance-run-id ci-quality --overwrite

score-disruptions-ci: validate-data-ci
	$(PYTHON) -m airline_operations_intelligence.cli score-disruptions --validation-report-dir reports/validation/ci-quality --config configs/disruption_scoring_ci.yaml --disruption-run-id ci-quality --overwrite

monitor-platform-ci: score-disruptions-ci forecast-passenger-demand-ci predict-flight-delays-ci analyse-aircraft-health-ci
	$(PYTHON) -m airline_operations_intelligence.cli monitor-platform --generation-run-dir data/raw/ci-quality --validation-report-dir reports/validation/ci-quality --passenger-forecast-report-dir reports/passenger_forecasting/ci-quality --delay-prediction-report-dir reports/delay_prediction/ci-quality --maintenance-report-dir reports/maintenance_analytics/ci-quality --disruption-report-dir reports/disruption_scoring/ci-quality --config configs/monitoring_ci.yaml --monitoring-run-id ci-quality --overwrite

run-operations-assistant-ci: monitor-platform-ci
	$(PYTHON) -m airline_operations_intelligence.cli run-operations-assistant --generation-run-dir data/raw/ci-quality --validation-report-dir reports/validation/ci-quality --passenger-forecast-report-dir reports/passenger_forecasting/ci-quality --delay-prediction-report-dir reports/delay_prediction/ci-quality --maintenance-report-dir reports/maintenance_analytics/ci-quality --disruption-report-dir reports/disruption_scoring/ci-quality --monitoring-report-dir reports/monitoring/ci-quality --config configs/genai_assistant_ci.yaml --intent executive_operations_brief --assistant-run-id ci-quality --overwrite

build-dashboard-outputs-ci: monitor-platform-ci
	$(PYTHON) -m airline_operations_intelligence.cli build-dashboard-outputs --generation-run-dir data/raw/ci-quality --validation-report-dir reports/validation/ci-quality --passenger-forecast-report-dir reports/passenger_forecasting/ci-quality --delay-prediction-report-dir reports/delay_prediction/ci-quality --maintenance-report-dir reports/maintenance_analytics/ci-quality --disruption-report-dir reports/disruption_scoring/ci-quality --monitoring-report-dir reports/monitoring/ci-quality --config configs/dashboard_outputs_ci.yaml --dashboard-run-id ci-quality --overwrite

test-data-generation:
	$(PYTHON) -m pytest tests/integration/test_data_generation.py

test-ingestion-validation:
	$(PYTHON) -m pytest tests/unit/test_validation_config.py tests/unit/test_ingestion_validation.py tests/integration/test_validation_pipeline.py

test-passenger-forecasting:
	$(PYTHON) -m pytest tests/unit/test_passenger_forecasting_config.py tests/unit/test_passenger_forecasting.py tests/integration/test_passenger_forecasting_pipeline.py

test-delay-prediction:
	$(PYTHON) -m pytest tests/unit/test_delay_prediction_config.py tests/unit/test_delay_prediction.py tests/integration/test_delay_prediction_pipeline.py

test-maintenance-analytics:
	$(PYTHON) -m pytest tests/unit/test_maintenance_analytics_config.py tests/unit/test_maintenance_analytics.py tests/integration/test_maintenance_analytics_pipeline.py

test-disruption-scoring:
	$(PYTHON) -m pytest tests/unit/test_disruption_scoring_config.py tests/unit/test_disruption_scoring.py tests/integration/test_disruption_scoring_pipeline.py

test-monitoring:
	$(PYTHON) -m pytest tests/unit/test_monitoring_config.py tests/unit/test_monitoring.py tests/integration/test_monitoring_pipeline.py

test-genai-assistant:
	$(PYTHON) -m pytest tests/unit/test_genai_assistant_config.py tests/unit/test_genai_assistant.py tests/integration/test_genai_assistant_pipeline.py

test-dashboard-outputs:
	$(PYTHON) -m pytest tests/unit/test_dashboard_outputs_config.py tests/unit/test_dashboard_outputs.py tests/integration/test_dashboard_outputs_pipeline.py

test-azure-architecture:
	$(PYTHON) -m pytest tests/unit/test_azure_architecture_mapping.py tests/integration/test_azure_architecture_static.py

describe-validation-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-validation --report-dir reports/validation/ci-quality

describe-passenger-forecast-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-passenger-forecast --forecast-report-dir reports/passenger_forecasting/ci-quality

describe-delay-prediction-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-delay-prediction --delay-report-dir reports/delay_prediction/ci-quality

describe-aircraft-health-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-aircraft-health --maintenance-report-dir reports/maintenance_analytics/ci-quality

describe-disruption-scoring-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-disruption-scoring --disruption-report-dir reports/disruption_scoring/ci-quality

describe-monitoring-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-monitoring --monitoring-report-dir reports/monitoring/ci-quality

describe-operations-assistant-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-operations-assistant --assistant-report-dir reports/genai_assistant/ci-quality

describe-dashboard-outputs-ci:
	$(PYTHON) -m airline_operations_intelligence.cli describe-dashboard-outputs --dashboard-report-dir reports/dashboard_outputs/ci-quality

quality: lint typecheck test docs-check yaml-check validate validate-azure-architecture generate-data-ci validate-data-ci forecast-passenger-demand-ci predict-flight-delays-ci analyse-aircraft-health-ci score-disruptions-ci monitor-platform-ci run-operations-assistant-ci build-dashboard-outputs-ci clean

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache build dist *.egg-info data/raw/ci-quality data/raw/.ci-quality.tmp data/interim/ci-quality data/interim/.ci-quality.tmp data/processed/ci-quality data/processed/.ci-quality.tmp reports/validation/ci-quality reports/validation/.ci-quality.tmp outputs/passenger_forecasting/ci-quality outputs/passenger_forecasting/.ci-quality.tmp outputs/models/passenger_forecasting/ci-quality outputs/models/passenger_forecasting/.ci-quality.tmp reports/passenger_forecasting/ci-quality reports/passenger_forecasting/.ci-quality.tmp outputs/delay_prediction/ci-quality outputs/delay_prediction/.ci-quality.tmp outputs/models/delay_prediction/ci-quality outputs/models/delay_prediction/.ci-quality.tmp reports/delay_prediction/ci-quality reports/delay_prediction/.ci-quality.tmp outputs/maintenance_analytics/ci-quality outputs/maintenance_analytics/.ci-quality.tmp reports/maintenance_analytics/ci-quality reports/maintenance_analytics/.ci-quality.tmp outputs/disruption_scoring/ci-quality outputs/disruption_scoring/.ci-quality.tmp reports/disruption_scoring/ci-quality reports/disruption_scoring/.ci-quality.tmp outputs/monitoring/ci-quality outputs/monitoring/.ci-quality.tmp reports/monitoring/ci-quality reports/monitoring/.ci-quality.tmp outputs/genai_assistant/ci-quality outputs/genai_assistant/.ci-quality.tmp reports/genai_assistant/ci-quality reports/genai_assistant/.ci-quality.tmp dashboard/outputs/ci-quality dashboard/outputs/.ci-quality.tmp reports/dashboard_outputs/ci-quality reports/dashboard_outputs/.ci-quality.tmp
