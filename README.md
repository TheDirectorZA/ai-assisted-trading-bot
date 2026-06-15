# ai-live-trading-bot

Local-first AI-assisted trading bot platform built with Django, FastAPI, Celery,
Redis, and a MetaTrader 5 live broker adapter.

## Live Trading Risk Warning

Real-money trading can lose money. This project is software, not financial
advice, and it does not promise profit. AI features are advisory only. AI cannot
approve trades, place orders, close positions, override risk settings, or circumvent
the kill switch.

Live MT5 execution is blocked unless every safety gate is satisfied:

- `TRADING_MODE=live`
- `LIVE_TRADING_ENABLED=true`
- `LIVE_TRADING_ARMED=true`
- `LIVE_CONFIRMATION_PHRASE=I_UNDERSTAND_REAL_MONEY_IS_AT_RISK`
- MT5 credentials are configured and the broker connection is healthy
- market data is fresh, the symbol and strategy are live enabled, stop loss is
  present, broker `order_check` passes, and the risk manager approves

## Features

- Django models, migrations, admin, and dashboard pages
- FastAPI execution service with `/docs`
- MT5 live broker adapter using the official `MetaTrader5` Python module
- Mock and paper brokers for safe local development
- Live ticks, candle sync, market-data health checks
- Moving Average Crossover, RSI Mean Reversion, and Breakout strategies
- Strict risk manager, risk-based position sizing, duplicate signal prevention
- Live order audit logs, risk events, position/order/account sync
- Mock AI provider by default, optional local Ollama provider
- Celery tasks for loop, sync, and report jobs
- Tests, linting, type checks, Docker Compose, and CI workflow

## Tech Stack

Python 3.12+, Django 5, Django REST Framework, FastAPI, Celery, Redis, SQLite
for local development, optional PostgreSQL in Docker Compose, Pydantic, Pytest,
Ruff, Black, and MyPy.

No paid AI API, paid market-data API, paid cloud hosting, SMS, or email service
is required.

## Local Setup

```bash
python3 -m pip install -e ".[dev]"
cp .env.example .env
python3 manage.py migrate
python3 manage.py seed_demo
python3 manage.py createsuperuser
```

Run Django:

```bash
make django
```

Run FastAPI:

```bash
make fastapi
```

Django dashboard: `http://127.0.0.1:8000/`
Admin: `http://127.0.0.1:8000/admin/`
FastAPI docs: `http://127.0.0.1:8001/docs`

## Docker Setup

```bash
docker-compose up --build
```

Compose starts Django, FastAPI, Redis, Celery worker, and Celery beat. The
PostgreSQL service is available behind the `postgres` profile.

MT5 live trading may require a desktop MT5 terminal running on the host. Do not
assume a Linux container can access a host desktop terminal without host-specific
setup.

## MT5 Configuration

Set these environment variables:

```bash
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
MT5_TERMINAL_PATH=
MT5_TIMEOUT_MS=60000
MT5_MAGIC_NUMBER=20260615
MT5_DEFAULT_DEVIATION_POINTS=20
```

Install the official package in an environment where it is supported:

```bash
python3 -m pip install ".[mt5]"
```

Check connection without placing trades:

```bash
make mt5-check
```

Sync account and positions:

```bash
make sync-account
make sync-positions
```

## Symbols, Strategies, And Risk

Use Django admin to configure:

- `TradingSymbol`: broker symbol mapping, spread limit, lot limits, live toggle
- `Strategy` and `StrategyParameter`: strategy config and live toggle
- `RiskSettings`: risk percentage, daily/weekly loss limits, max positions,
  stop-loss rules, spread, slippage, stale-data threshold, and allowed symbols

Defaults are conservative: symbols and strategies are not live enabled.

## Arming And Starting Live Trading

Set the exact live environment gates first:

```bash
TRADING_MODE=live
LIVE_TRADING_ENABLED=true
LIVE_TRADING_ARMED=true
LIVE_CONFIRMATION_PHRASE=I_UNDERSTAND_REAL_MONEY_IS_AT_RISK
```

Then explicitly start:

```bash
python3 manage.py start_live_bot \
  --symbol EURUSD \
  --strategy moving-average-crossover \
  --confirm I_UNDERSTAND_REAL_MONEY_IS_AT_RISK
```

Stop:

```bash
make kill-switch
python3 manage.py stop_live_bot
```

The dashboard includes a live warning banner and an `ACTIVATE KILL SWITCH`
button.

## Manual Real Order Test

This command can place a real MT5 market order. It refuses to run without the
exact real-order phrase and a stop loss.

```bash
python3 manage.py mt5_test_order \
  --symbol XAUUSD \
  --volume 0.01 \
  --stop-loss 1900 \
  --confirm I_UNDERSTAND_THIS_PLACES_A_REAL_TRADE
```

## Verification

```bash
make test
make lint
make typecheck
make migrate
make seed
make backtest
```

## Known Limitations

- MT5 live connectivity must be checked manually with the user's broker terminal.
- The default database is SQLite for local use; PostgreSQL should be used for
  production-like multi-process operation.
- The included strategies are educational examples and not profit promises.
- News filtering and advanced portfolio exposure controls require broker/data
  specific configuration before real-money use.

Read the full docs in `docs/` before connecting a live broker account.
