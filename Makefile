.PHONY: install lint test test-learning test-learning-mps check format authoring-check web-build play
install:
	uv sync --locked
	uv run python scripts/bootstrap_agents.py
	npm ci --prefix web
lint:
	uv run ruff check src scripts tests conftest.py
	uv run ruff format --check src scripts tests conftest.py
	uv run python scripts/check_docs.py
	npm run check --prefix web
	web/node_modules/.bin/prettier --check src/qi/experiments/report.html src/qi/experiments/report.css src/qi/experiments/report.js src/qi/experiments/report-help.js
	node --check src/qi/experiments/report.js
	node --check src/qi/experiments/report-help.js
test:
	uv run pytest
	npm test --prefix web
test-learning:
	uv run --locked --extra learning pytest tests/test_learning.py tests/test_learning_config.py
test-learning-mps:
	QI_TEST_MPS=1 uv run --locked --extra learning pytest tests/test_learning_mps.py
check: lint test web-build
format:
	uv run ruff check --fix src scripts tests conftest.py
	uv run ruff format src scripts tests conftest.py
	npm run format --prefix web
	web/node_modules/.bin/prettier --write src/qi/experiments/report.html src/qi/experiments/report.css src/qi/experiments/report.js src/qi/experiments/report-help.js
authoring-check:
	uv run python scripts/check_authoring.py

web-build:
	npm run build --prefix web
play: web-build
	uv run qi play
