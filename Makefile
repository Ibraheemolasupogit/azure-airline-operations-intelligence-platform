PYTHON ?= python3

.PHONY: install format lint typecheck test docs-check yaml-check validate generate-data-ci test-data-generation quality clean

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

test-data-generation:
	$(PYTHON) -m pytest tests/integration/test_data_generation.py

quality: lint typecheck test docs-check yaml-check validate generate-data-ci

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache build dist *.egg-info data/raw/ci-quality data/raw/.ci-quality.tmp
