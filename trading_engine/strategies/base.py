from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

SignalType = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True, slots=True)
class CandleData:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class StrategyContext:
    symbol: str
    timeframe: str = "M5"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StrategySignal:
    signal_type: SignalType
    timestamp: datetime
    price: Decimal
    confidence: Decimal
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    name: str
    slug: str

    def __init__(self, parameters: dict[str, Any] | None = None) -> None:
        self.parameters = parameters or {}
        self.validate_parameters()

    @abstractmethod
    def validate_parameters(self) -> None: ...

    @abstractmethod
    def generate_signal(
        self, candles: list[CandleData], context: StrategyContext
    ) -> StrategySignal: ...

    def calculate_stop_loss(
        self,
        signal: StrategySignal,
        candles: list[CandleData],
        context: StrategyContext,
    ) -> Decimal | None:
        if signal.signal_type == "HOLD" or not candles:
            return None
        lookback = int(self.parameters.get("stop_loss_lookback", 5))
        recent = candles[-lookback:]
        if signal.signal_type == "BUY":
            return min(candle.low for candle in recent)
        return max(candle.high for candle in recent)

    def calculate_take_profit(
        self,
        signal: StrategySignal,
        candles: list[CandleData],
        context: StrategyContext,
    ) -> Decimal | None:
        stop_loss = self.calculate_stop_loss(signal, candles, context)
        if signal.signal_type == "HOLD" or stop_loss is None:
            return None
        reward_risk = Decimal(str(self.parameters.get("reward_risk", "2")))
        risk = abs(signal.price - stop_loss)
        if signal.signal_type == "BUY":
            return signal.price + risk * reward_risk
        return signal.price - risk * reward_risk

    def explain_signal(
        self,
        signal: StrategySignal,
        candles: list[CandleData],
        context: StrategyContext,
    ) -> str:
        return f"{self.name} emitted {signal.signal_type} for {context.symbol}: {signal.reason}"

    @staticmethod
    def _hold(candles: list[CandleData], reason: str) -> StrategySignal:
        if candles:
            latest = candles[-1]
            return StrategySignal("HOLD", latest.timestamp, latest.close, Decimal("0"), reason)
        return StrategySignal("HOLD", datetime.fromtimestamp(0), Decimal("0"), Decimal("0"), reason)
