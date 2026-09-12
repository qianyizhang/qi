.PHONY: install lint test test-learning test-learning-mps test-data check format authoring-check web-build play
install:
	uv sync --locked
	uv run python scripts/bootstrap_agents.py
	npm ci --prefix web
lint:
	uv run ruff check src scripts tests conftest.py
	uv run ruff format --check src scripts tests conftest.py
	uv run python scripts/check_docs.py
	uv run qi experiment check-catalog --summary
	uv run python scripts/export_openapi.py --check
	npm run check --prefix web
test: web-build
	uv run pytest
	npm test --prefix web
test-learning:
	uv run --locked --extra learning pytest tests/test_learning.py tests/test_learning_config.py tests/test_training_data.py tests/test_reference.py
test-data:
	uv run --locked --extra data --extra learning pytest src/qi/training_data/test_store.py src/qi/training_data/test_generation_runner.py tests/test_collection_learning.py tests/test_snapshot_training.py tests/test_semantic_selection.py
test-learning-mps:
	QI_TEST_MPS=1 uv run --locked --extra learning pytest tests/test_learning_mps.py
check: lint test
format:
	uv run ruff check --fix src scripts tests conftest.py
	uv run ruff format src scripts tests conftest.py
	npm run format --prefix web
authoring-check:
	uv run python scripts/check_authoring.py

web-build:
	npm run build --prefix web
play: web-build
	uv run qi play
