from __future__ import annotations

from decimal import Decimal

from trading_engine.strategies.base import BaseStrategy, CandleData, StrategyContext, StrategySignal


class BreakoutStrategy(BaseStrategy):
    name = "Breakout Strategy"
    slug = "breakout"

    def validate_parameters(self) -> None:
        lookback = int(self.parameters.get("lookback", 20))
        if lookback <= 1:
            raise ValueError("breakout lookback must be greater than one")

    def generate_signal(
        self, candles: list[CandleData], context: StrategyContext
    ) -> StrategySignal:
        lookback = int(self.parameters.get("lookback", 20))
        if len(candles) < lookback + 1:
            return self._hold(candles, "not enough candles for breakout")
        latest = candles[-1]
        previous = candles[-(lookback + 1) : -1]
        prior_high = max(candle.high for candle in previous)
        prior_low = min(candle.low for candle in previous)
        if latest.close > prior_high:
            return StrategySignal(
                "BUY",
                latest.timestamp,
                latest.close,
                Decimal("0.68"),
                "close broke above lookback high",
                {"prior_high": str(prior_high)},
            )
        if latest.close < prior_low:
            return StrategySignal(
                "SELL",
                latest.timestamp,
                latest.close,
                Decimal("0.68"),
                "close broke below lookback low",
                {"prior_low": str(prior_low)},
            )
        return self._hold(candles, "no breakout")
