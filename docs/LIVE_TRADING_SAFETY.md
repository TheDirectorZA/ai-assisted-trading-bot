# Live Trading Safety

Live mode requires:

- `TRADING_MODE=live`
- `LIVE_TRADING_ENABLED=true`
- `LIVE_TRADING_ARMED=true`
- `LIVE_CONFIRMATION_PHRASE=I_UNDERSTAND_REAL_MONEY_IS_AT_RISK`

Dangerous controls require confirmation phrases. Manual MT5 test orders require
`I_UNDERSTAND_THIS_PLACES_A_REAL_TRADE`.

The kill switch stops bot loops and blocks new orders. It can be activated from
the dashboard, API, or `python manage.py activate_kill_switch`. Reset requires
manual confirmation.

The risk manager checks broker connection, account permission, symbol/strategy
live flags, spread, stale data, price jumps, stop loss, take profit rules,
position size, loss limits, open-position limits, leverage, margin, trading
hours, duplicate signals, and broker `order_check`.

Every blocked trade creates a `RiskEvent` and `AuditLog`.
