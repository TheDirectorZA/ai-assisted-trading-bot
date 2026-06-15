PYTHON ?= python3
MANAGE = $(PYTHON) manage.py

.PHONY: setup migrate makemigrations createsuperuser seed test lint format typecheck django fastapi celery-worker celery-beat docker-up docker-down backtest mt5-check sync-account sync-positions kill-switch check

setup:
	$(PYTHON) -m pip install -e ".[dev]"

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

createsuperuser:
	$(MANAGE) createsuperuser

seed:
	$(MANAGE) seed_demo

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m black .
	$(PYTHON) -m ruff check --fix .

typecheck:
	$(PYTHON) -m mypy trading_engine fastapi_app

django:
	$(MANAGE) runserver 0.0.0.0:8000

fastapi:
	$(PYTHON) -m uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8001

celery-worker:
	celery -A ai_live_trading_bot worker -l info

celery-beat:
	celery -A ai_live_trading_bot beat -l info

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down --volumes

backtest:
	$(MANAGE) run_demo_backtest

mt5-check:
	$(MANAGE) mt5_check_connection

sync-account:
	$(MANAGE) mt5_sync_account

sync-positions:
	$(MANAGE) mt5_sync_positions

kill-switch:
	$(MANAGE) activate_kill_switch

check: test lint typecheck migrate seed backtest
