from __future__ import annotations

from decimal import Decimal

from trading_engine.strategies.base import BaseStrategy, CandleData, StrategyContext, StrategySignal


class RSIMeanReversionStrategy(BaseStrategy):
    name = "RSI Mean Reversion"
    slug = "rsi-mean-reversion"

    def validate_parameters(self) -> None:
        period = int(self.parameters.get("period", 14))
        lower = Decimal(str(self.parameters.get("lower", "30")))
        upper = Decimal(str(self.parameters.get("upper", "70")))
        if period <= 1:
            raise ValueError("RSI period must be greater than one")
        if lower >= upper:
            raise ValueError("RSI lower threshold must be below upper threshold")

    def generate_signal(
        self, candles: list[CandleData], context: StrategyContext
    ) -> StrategySignal:
        period = int(self.parameters.get("period", 14))
        lower = Decimal(str(self.parameters.get("lower", "30")))
        upper = Decimal(str(self.parameters.get("upper", "70")))
        if len(candles) < period + 1:
            return self._hold(candles, "not enough candles for RSI")

        rsi = _rsi(candles[-(period + 1) :])
        latest = candles[-1]
        if rsi <= lower:
            return StrategySignal(
                "BUY",
                latest.timestamp,
                latest.close,
                Decimal("0.65"),
                f"RSI {rsi} is below lower threshold {lower}",
                {"rsi": str(rsi)},
            )
        if rsi >= upper:
            return StrategySignal(
                "SELL",
                latest.timestamp,
                latest.close,
                Decimal("0.65"),
                f"RSI {rsi} is above upper threshold {upper}",
                {"rsi": str(rsi)},
            )
        return self._hold(candles, f"RSI {rsi} is neutral")


def _rsi(candles: list[CandleData]) -> Decimal:
    gains = Decimal("0")
    losses = Decimal("0")
    for previous, current in zip(candles, candles[1:], strict=False):
        change = current.close - previous.close
        if change >= 0:
            gains += change
        else:
            losses += abs(change)
    if losses == 0:
        return Decimal("100")
    relative_strength = gains / losses
    return (Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))).quantize(
        Decimal("0.01")
    )
