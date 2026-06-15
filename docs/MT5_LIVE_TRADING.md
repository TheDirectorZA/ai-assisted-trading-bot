# MT5 Live Trading

Install MetaTrader 5 from your broker and log into the terminal manually first.
The official `MetaTrader5` Python package must be installed in an environment
where it supports your operating system and terminal.

Required variables:

```bash
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
MT5_TERMINAL_PATH=
MT5_TIMEOUT_MS=60000
MT5_MAGIC_NUMBER=20260615
MT5_DEFAULT_DEVIATION_POINTS=20
```

Connection check:

```bash
python3 manage.py mt5_check_connection
```

Sync account and positions:

```bash
python3 manage.py mt5_sync_account
python3 manage.py mt5_sync_positions
```

Sync symbol metadata:

```bash
python3 manage.py mt5_sync_symbols EURUSD XAUUSD
```

The adapter selects hidden symbols when possible, checks trade mode, retrieves
ticks and candles, builds MT5 request dictionaries, runs `order_check`, sends
orders with `order_send`, handles retcodes, and stores raw broker responses.

Common retcodes include `TRADE_RETCODE_DONE`, `TRADE_RETCODE_PLACED`,
`TRADE_RETCODE_DONE_PARTIAL`, and broker-specific rejection codes. `order_check`
is required because the terminal can reject invalid volume, margin, stops, or
symbol settings before `order_send`. `order_send` can still fail because prices,
spread, session state, or margin can change after the pre-check.

Docker note: desktop MT5 terminal access from containers is host-specific. Run
the live broker worker on the host if the container cannot reach the terminal.
