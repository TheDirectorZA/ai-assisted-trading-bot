# Strategy Guide

Strategies inherit from `BaseStrategy` and implement:

- `validate_parameters`
- `generate_signal`
- `calculate_stop_loss`
- `calculate_take_profit`
- `explain_signal`

Included strategies:

- Moving Average Crossover
- RSI Mean Reversion
- Breakout Strategy

Strategies are deterministic and only produce `BUY`, `SELL`, or `HOLD` signals.
They never execute orders.
