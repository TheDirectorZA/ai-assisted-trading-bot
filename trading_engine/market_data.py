from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from trading_engine.brokers.base import BaseBroker, BrokerTick
from trading_engine.configuration import LiveTradingSettings
from trading_engine.models import (
    Candle,
    LiveCandleSyncLog,
    LiveTick,
    MarketDataHealthCheck,
    TradingSymbol,
)


def persist_live_tick(symbol: TradingSymbol, tick: BrokerTick) -> LiveTick:
    spread_points = (tick.ask - tick.bid) / symbol.point if symbol.point else Decimal("0")
    return LiveTick.objects.create(
        symbol=symbol,
        broker_time=tick.broker_time,
        local_time=timezone.now(),
        bid=tick.bid,
        ask=tick.ask,
        last=tick.last,
        volume=tick.volume,
        spread_points=spread_points,
    )


def sync_candles(
    *,
    broker: BaseBroker,
    symbol: TradingSymbol,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> LiveCandleSyncLog:
    log = LiveCandleSyncLog.objects.create(symbol=symbol, timeframe=timeframe)
    created = 0
    updated = 0
    try:
        for row in broker.get_historical_rates(symbol.broker_symbol, timeframe, start, end):
            _, was_created = Candle.objects.update_or_create(
                symbol=symbol,
                timestamp=row["timestamp"],
                timeframe=timeframe,
                source="MT5",
                defaults={
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        log.status = "COMPLETED"
        log.message = "candle sync completed"
    except Exception as exc:
        log.status = "FAILED"
        log.message = str(exc)
    finally:
        log.completed_at = timezone.now()
        log.candles_created = created
        log.candles_updated = updated
        log.save()
    return log


def check_market_data_health(symbol: TradingSymbol) -> MarketDataHealthCheck:
    settings = LiveTradingSettings.from_env()
    now = timezone.now()
    tick = LiveTick.objects.filter(symbol=symbol).order_by("-broker_time").first()
    candle = (
        Candle.objects.filter(symbol=symbol, timeframe=symbol.timeframe)
        .order_by("-timestamp")
        .first()
    )
    tick_age = int((now - tick.broker_time).total_seconds()) if tick else None
    candle_age = int((now - candle.timestamp).total_seconds()) if candle else None
    spread = tick.spread_points if tick else None
    is_fresh = (
        tick_age is not None
        and candle_age is not None
        and tick_age <= settings.max_tick_age_seconds
        and candle_age <= settings.max_candle_age_seconds
    )
    message = "market data fresh" if is_fresh else "market data stale or missing"
    return MarketDataHealthCheck.objects.create(
        symbol=symbol,
        latest_tick_at=tick.broker_time if tick else None,
        latest_candle_at=candle.timestamp if candle else None,
        tick_age_seconds=tick_age,
        candle_age_seconds=candle_age,
        is_fresh=is_fresh,
        spread_points=spread,
        message=message,
    )


def price_jump_percentage(previous_price: Decimal, current_price: Decimal) -> Decimal:
    if previous_price <= 0:
        return Decimal("0")
    return (abs(current_price - previous_price) / previous_price * Decimal("100")).quantize(
        Decimal("0.0001")
    )
