.PHONY: install lint test check format authoring-check web-build play
install:
	uv sync --locked
	uv run python scripts/bootstrap_agents.py
	npm ci --prefix web
lint:
	uv run ruff check src scripts tests
	uv run ruff format --check src scripts tests
	uv run python scripts/check_docs.py
	npm run check --prefix web
test:
	uv run pytest
	npm test --prefix web
check: lint test web-build
format:
	uv run ruff check --fix src scripts tests
	uv run ruff format src scripts tests
	npm run format --prefix web
authoring-check:
	uv run python scripts/check_authoring.py

web-build:
	npm run build --prefix web
play: web-build
	uv run qi play
