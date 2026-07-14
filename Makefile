.PHONY: setup format format-check lint typecheck test harness-smoke check

setup:
	uv sync --dev

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

harness-smoke:
	uv run repolens harness-smoke

check: format-check lint typecheck test harness-smoke
