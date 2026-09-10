.PHONY: install lint test test-learning test-learning-mps check format authoring-check web-build play
install:
	uv sync --locked
	uv run python scripts/bootstrap_agents.py
	npm ci --prefix web
lint:
	uv run ruff check src scripts tests conftest.py
	uv run ruff format --check src scripts tests conftest.py
	uv run python scripts/check_docs.py
	uv run qi experiment check-catalog --summary
	npm run check --prefix web
test: web-build
	uv run pytest
	npm test --prefix web
test-learning:
	uv run --locked --extra learning pytest tests/test_learning.py tests/test_learning_config.py tests/test_training_data.py tests/test_reference.py
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
