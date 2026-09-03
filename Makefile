.PHONY: demo install dev test clean db-upgrade format lint

demo: install db-upgrade
	@echo "🚀 Starting Asyncraft Agent Kernel demo..."
	@echo "   Web UI: http://localhost:8000"
	@echo "   API docs: http://localhost:8000/docs"
	@echo ""
	@echo "   Default skin: ops_dispatch"
	@echo "   To switch: ACTIVE_SKIN=deal_flow make dev"
	@echo ""
	uvicorn asynccraft.main:app --host 0.0.0.0 --port 8000 --reload

install:
	pip install -e ".[dev]"

dev: db-upgrade
	uvicorn asynccraft.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ -v

db-upgrade:
	@echo "📊 Running database migrations..."
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-reset:
	rm -f asynccraft.db
	alembic upgrade head

format:
	black asynccraft/ tests/
	ruff check --fix asynccraft/ tests/

lint:
	black --check asynccraft/ tests/
	ruff check asynccraft/ tests/
	mypy asynccraft/

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
