# Risk Management

Default sizing is risk based:

```text
volume = account risk amount / stop-distance value per lot
```

Inputs include account equity, risk percentage, entry price, stop loss, symbol
point, lot step, min/max lot, broker max lot, and configured max lot.

The system blocks trades when:

- stop loss is missing or outside configured distance limits
- spread or slippage limits are exceeded
- market data is stale
- daily or weekly loss limits are reached
- max open position limits are reached
- free margin is insufficient
- duplicate signal has already been processed
- broker `order_check` fails

Risk settings are stored per user and editable through Django admin.
