.PHONY: dev install clean test lint migrate neo4j-init seed-search

install:
	uv run python scripts/patches.py

test:
	uv run pytest

lint:
	uv run ruff check .

migrate:
	uv run alembic upgrade head

neo4j-init:
	uv run python -m scripts.neo4j.init

seed-search:
	uv run python -m scripts.neo4j.seed_search_graph

dev:
	@if [ -f .env ]; then \
		echo ".env detected"; \
		set -a && . ./.env && set +a && ENV=development uv run python main.py; \
	else \
		echo " .env 파일이 없습니다!"; \
		ENV=development uv run python main.py; \
	fi

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
