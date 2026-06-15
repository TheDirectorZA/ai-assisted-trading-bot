from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from trading_engine.models import BacktestRun, BacktestTrade, Candle, Strategy, TradingSymbol
from trading_engine.strategies import (
    BaseStrategy,
    BreakoutStrategy,
    CandleData,
    MovingAverageCrossoverStrategy,
    RSIMeanReversionStrategy,
    StrategyContext,
)

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    MovingAverageCrossoverStrategy.slug: MovingAverageCrossoverStrategy,
    RSIMeanReversionStrategy.slug: RSIMeanReversionStrategy,
    BreakoutStrategy.slug: BreakoutStrategy,
}


@dataclass(frozen=True, slots=True)
class BacktestTradeRecord:
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    side: str
    pnl: Decimal
    exit_reason: str


def strategy_from_model(strategy: Strategy) -> BaseStrategy:
    parameters = {
        param.name: _coerce_value(param.value, param.value_type)
        for param in strategy.parameters.all()
    }
    strategy_class = STRATEGY_REGISTRY.get(strategy.slug)
    if strategy_class is None:
        raise ValueError(f"strategy implementation not registered: {strategy.slug}")
    return strategy_class(parameters)


def run_backtest(
    *,
    symbol: TradingSymbol,
    strategy_model: Strategy,
    initial_balance: Decimal = Decimal("10000"),
) -> BacktestRun:
    candles = [
        CandleData(
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        for candle in Candle.objects.filter(symbol=symbol, timeframe=symbol.timeframe).order_by(
            "timestamp"
        )
    ]
    if len(candles) < 5:
        raise ValueError("not enough candles for demo backtest")

    strategy = strategy_from_model(strategy_model)
    context = StrategyContext(symbol=symbol.symbol, timeframe=symbol.timeframe)
    cash = initial_balance
    quantity = Decimal("0")
    entry_price: Decimal | None = None
    entry_time = candles[0].timestamp
    trade_records: list[BacktestTradeRecord] = []
    equity_curve: list[Decimal] = []

    for index in range(1, len(candles)):
        window = candles[: index + 1]
        signal = strategy.generate_signal(window, context)
        latest = window[-1]
        if signal.signal_type == "BUY" and quantity == 0:
            quantity = (cash / latest.close).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
            if quantity > 0:
                cash -= quantity * latest.close
                entry_price = latest.close
                entry_time = latest.timestamp
        elif signal.signal_type == "SELL" and quantity > 0 and entry_price is not None:
            cash += quantity * latest.close
            pnl = (latest.close - entry_price) * quantity
            trade_records.append(
                BacktestTradeRecord(
                    entry_time=entry_time,
                    exit_time=latest.timestamp,
                    entry_price=entry_price,
                    exit_price=latest.close,
                    quantity=quantity,
                    side="BUY",
                    pnl=pnl,
                    exit_reason=signal.reason,
                )
            )
            quantity = Decimal("0")
            entry_price = None
        equity_curve.append(cash + quantity * latest.close)

    if quantity > 0 and entry_price is not None:
        latest = candles[-1]
        cash += quantity * latest.close
        pnl = (latest.close - entry_price) * quantity
        trade_records.append(
            BacktestTradeRecord(
                entry_time=entry_time,
                exit_time=latest.timestamp,
                entry_price=entry_price,
                exit_price=latest.close,
                quantity=quantity,
                side="BUY",
                pnl=pnl,
                exit_reason="final liquidation",
            )
        )

    final_balance = cash.quantize(Decimal("0.01"))
    total_return = ((final_balance - initial_balance) / initial_balance * Decimal("100")).quantize(
        Decimal("0.0001")
    )
    winning = [trade for trade in trade_records if trade.pnl > 0]
    gross_profit = sum((trade.pnl for trade in trade_records if trade.pnl > 0), Decimal("0"))
    gross_loss = abs(sum((trade.pnl for trade in trade_records if trade.pnl < 0), Decimal("0")))
    profit_factor = (
        (gross_profit / gross_loss).quantize(Decimal("0.0001")) if gross_loss else Decimal("0")
    )
    win_rate = (
        (Decimal(len(winning)) / Decimal(len(trade_records)) * Decimal("100")).quantize(
            Decimal("0.0001")
        )
        if trade_records
        else Decimal("0")
    )

    backtest = BacktestRun.objects.create(
        strategy=strategy_model,
        symbol=symbol,
        start_date=candles[0].timestamp,
        end_date=candles[-1].timestamp,
        initial_balance=initial_balance,
        final_balance=final_balance,
        total_return=total_return,
        max_drawdown=_max_drawdown(equity_curve),
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=len(trade_records),
        parameters={param.name: param.value for param in strategy_model.parameters.all()},
        metrics_json={"equity_points": len(equity_curve)},
    )
    for trade in trade_records:
        BacktestTrade.objects.create(
            backtest_run=backtest,
            symbol=symbol,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            quantity=trade.quantity,
            side=trade.side,
            pnl=trade.pnl,
            pnl_percentage=(trade.pnl / initial_balance * Decimal("100")).quantize(
                Decimal("0.0001")
            ),
            exit_reason=trade.exit_reason,
        )
    return backtest


def _max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    if not equity_curve:
        return Decimal("0")
    peak = equity_curve[0]
    max_drawdown = Decimal("0")
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = (peak - equity) / peak * Decimal("100")
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return max_drawdown.quantize(Decimal("0.0001"))


def _coerce_value(value: str, value_type: str) -> object:
    if value_type == "int":
        return int(value)
    if value_type == "decimal":
        return Decimal(value)
    if value_type == "bool":
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return value
