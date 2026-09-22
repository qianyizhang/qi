.PHONY: install install-hooks lint lint-python lint-metadata format authoring-check check
.PHONY: test test-game test-native test-learning test-learning-mps test-data test-reference-package test-e2e
.PHONY: web-build play

PYTHON_PATHS := packages src scripts tests conftest.py web/e2e/prepare.py
REFERENCE_PACKAGE_OUTPUT ?= artifacts/reference-package
E2E_ARGS ?=

install:
	uv sync --locked --inexact
	uv run --locked python scripts/bootstrap_agents.py
	npm ci --prefix web
	$(MAKE) install-hooks
install-hooks:
	uv run --locked pre-commit install
lint: lint-python lint-metadata
	uv run --locked pre-commit validate-config
	npm run check --prefix web
lint-python:
	uv run --locked ruff check $(PYTHON_PATHS)
	uv run --locked ruff format --check $(PYTHON_PATHS)
lint-metadata:
	uv run --locked python scripts/check_checkout_docs.py
	uv run --locked qi experiment check-catalog --verify-evidence --summary
	uv run --locked python scripts/export_openapi.py --check
test: web-build
	uv run --locked pytest
	npm test --prefix web
test-game:
	uv run --locked python scripts/check_game_package.py
test-native:
	uv run --locked --extra native python scripts/check_game_package.py --native
	uv run --locked --extra native pytest tests/test_native_generation.py
test-learning:
	uv run --locked --extra learning pytest tests/test_learning.py tests/test_learning_config.py tests/test_training_data.py tests/test_reference.py
test-data:
	uv run --locked --extra data --extra learning pytest src/qi/training_data/test_store.py src/qi/training_data/test_generation_runner.py tests/test_collection_learning.py tests/test_snapshot_training.py tests/test_semantic_selection.py
test-learning-mps:
	QI_TEST_MPS=1 uv run --locked --extra learning pytest tests/test_learning_mps.py
test-reference-package:
	uv run --locked --extra learning python scripts/check_reference_package.py --output $(REFERENCE_PACKAGE_OUTPUT)
test-e2e:
	npm run test:e2e --prefix web -- $(E2E_ARGS)
check: lint test
format:
	uv run --locked ruff check --fix $(PYTHON_PATHS)
	uv run --locked ruff format $(PYTHON_PATHS)
	npm run format --prefix web
authoring-check:
	uv run --locked python scripts/check_authoring.py

web-build:
	npm run build --prefix web
play: web-build
	uv run --locked qi play
