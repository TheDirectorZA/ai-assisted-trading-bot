# Troubleshooting

MT5 connection fails:

- Confirm the terminal is installed and logged in.
- Check `MT5_LOGIN`, `MT5_SERVER`, and `MT5_TERMINAL_PATH`.
- Run `python3 manage.py mt5_check_connection`.

Order blocked:

- Review `RiskEvent` and `AuditLog`.
- Check stop loss, spread, stale data, symbol live flag, strategy live flag, and
  broker `order_check` response.

FastAPI cannot read database rows:

- Run `python3 manage.py migrate`.
- Confirm `DATABASE_URL` points at the expected database.

Celery tasks do not run:

- Start Redis.
- Start worker with `make celery-worker`.
- Start beat with `make celery-beat`.
