from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_engine.strategies import (
    BreakoutStrategy,
    CandleData,
    MovingAverageCrossoverStrategy,
    RSIMeanReversionStrategy,
    StrategyContext,
)


def _candles(values: list[str]) -> list[CandleData]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        CandleData(
            timestamp=start + timedelta(minutes=index),
            open=Decimal(value),
            high=Decimal(value) + Decimal("1"),
            low=Decimal(value) - Decimal("1"),
            close=Decimal(value),
        )
        for index, value in enumerate(values)
    ]


def test_moving_average_strategy_emits_signal() -> None:
    strategy = MovingAverageCrossoverStrategy({"short_window": 2, "long_window": 3})
    signal = strategy.generate_signal(
        _candles(["10", "9", "8", "10", "12"]),
        StrategyContext(symbol="DEMO"),
    )

    assert signal.signal_type in {"BUY", "SELL", "HOLD"}
    assert "Moving Average" in strategy.explain_signal(signal, [], StrategyContext(symbol="DEMO"))


def test_rsi_strategy_is_deterministic() -> None:
    strategy = RSIMeanReversionStrategy({"period": 3, "lower": "30", "upper": "70"})
    signal = strategy.generate_signal(
        _candles(["10", "9", "8", "7", "6"]),
        StrategyContext(symbol="DEMO"),
    )

    assert signal.signal_type == "BUY"


def test_breakout_strategy_emits_buy_on_new_high() -> None:
    strategy = BreakoutStrategy({"lookback": 3})
    signal = strategy.generate_signal(
        _candles(["10", "11", "12", "14"]),
        StrategyContext(symbol="DEMO"),
    )

    assert signal.signal_type == "BUY"
