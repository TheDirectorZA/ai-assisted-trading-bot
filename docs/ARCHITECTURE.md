# Architecture

The platform separates responsibilities:

- Django owns persistence, migrations, admin, dashboard pages, and operational
  commands.
- FastAPI exposes the execution-service HTTP API and OpenAPI docs.
- `trading_engine.brokers` defines the broker interface and MT5 implementation.
- `trading_engine.strategies` emits deterministic signals only.
- `trading_engine.risk` is the final software gate before any broker order send.
- `trading_engine.execution` orchestrates account sync, signal generation,
  order pre-checks, risk decisions, audit logs, and execution.
- Celery runs repeatable background sync and live-loop tasks.

Live execution flow:

1. Load bot state and risk settings.
2. Connect to broker and sync account/positions.
3. Fetch fresh market data.
4. Generate a strategy signal.
5. Build an order request with stop loss.
6. Run broker `order_check`.
7. Ask the risk manager for a decision.
8. Create audit records.
9. Call `order_send` only in live mode with all gates satisfied.
10. Sync positions and journal the outcome.
