# Convenience Makefile for common development tasks.
# All commands assume the virtual environment is active.

.DEFAULT_GOAL := help

.PHONY: help install dev lint format test test-unit test-integration test-e2e coverage clean ci

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

ci: lint format-check test ## Run full local CI (lint + format check + tests)

install: ## Install the package in editable mode
	pip install -e .

dev: ## Install with dev dependencies
	pip install -e ".[dev]"

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/

format-check: ## Check code formatting
	ruff format --check src/ tests/

test: ## Run all tests (excluding network and benchmark)
	pytest -m "not network and not benchmark" --tb=short

test-unit: ## Run unit tests only
	pytest tests/unit/ --tb=short -q

test-integration: ## Run integration tests only
	pytest tests/integration/ --tb=short -q

test-e2e: ## Run end-to-end CLI tests
	pytest tests/e2e/ --tb=short -q

coverage: ## Run tests with coverage report
	pytest --cov=keyline_planner --cov-report=term-missing --cov-report=html \
		-m "not network and not benchmark"

benchmark: ## Run performance benchmarks
	pytest -m benchmark --benchmark-only

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf .benchmarks/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
