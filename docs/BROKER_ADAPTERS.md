# Broker Adapters

Broker adapters live in `trading_engine/brokers`:

- `base.py`: required broker interface and data classes
- `mock_broker.py`: deterministic local broker for tests
- `paper_broker.py`: safe paper broker
- `mt5_live_broker.py`: real MT5 adapter
- `exceptions.py`: broker-specific exceptions

`MT5LiveBroker` connects to the terminal, retrieves account/symbol/tick/candle
data, calculates margin/profit, builds requests, runs `order_check`, sends real
orders, closes positions, syncs positions, and syncs orders.

Credentials are loaded only from environment variables and passwords are never
logged.
