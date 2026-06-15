from __future__ import annotations

from decimal import Decimal

from trading_engine.strategies.base import BaseStrategy, CandleData, StrategyContext, StrategySignal


class MovingAverageCrossoverStrategy(BaseStrategy):
    name = "Moving Average Crossover"
    slug = "moving-average-crossover"

    def validate_parameters(self) -> None:
        short_window = int(self.parameters.get("short_window", 5))
        long_window = int(self.parameters.get("long_window", 20))
        if short_window <= 0 or long_window <= 0:
            raise ValueError("moving-average windows must be positive")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")

    def generate_signal(
        self, candles: list[CandleData], context: StrategyContext
    ) -> StrategySignal:
        short_window = int(self.parameters.get("short_window", 5))
        long_window = int(self.parameters.get("long_window", 20))
        if len(candles) < long_window + 1:
            return self._hold(candles, "not enough candles for crossover")

        previous = candles[:-1]
        latest = candles[-1]
        prev_short = _average(previous[-short_window:])
        prev_long = _average(previous[-long_window:])
        curr_short = _average(candles[-short_window:])
        curr_long = _average(candles[-long_window:])

        if prev_short <= prev_long and curr_short > curr_long:
            return StrategySignal(
                "BUY",
                latest.timestamp,
                latest.close,
                Decimal("0.72"),
                "short moving average crossed above long moving average",
                {"short_ma": str(curr_short), "long_ma": str(curr_long)},
            )
        if prev_short >= prev_long and curr_short < curr_long:
            return StrategySignal(
                "SELL",
                latest.timestamp,
                latest.close,
                Decimal("0.72"),
                "short moving average crossed below long moving average",
                {"short_ma": str(curr_short), "long_ma": str(curr_long)},
            )
        return self._hold(candles, "no moving-average crossover")


def _average(candles: list[CandleData]) -> Decimal:
    return sum((candle.close for candle in candles), Decimal("0")) / Decimal(len(candles))
