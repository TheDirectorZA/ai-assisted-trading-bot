from __future__ import annotations

import os
from dataclasses import asdict
from decimal import Decimal
from typing import Any, cast

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_live_trading_bot.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from trading_engine.ai import get_ai_provider
from trading_engine.backtesting import run_backtest
from trading_engine.brokers import MT5LiveBroker, OrderRequest
from trading_engine.brokers.base import OrderSide
from trading_engine.configuration import CONFIRMATION_PHRASE, LiveTradingSettings
from trading_engine.models import (
    AuditLog,
    BotState,
    BrokerAccount,
    LiveOrder,
    RiskEvent,
    Signal,
    Strategy,
    TradingSymbol,
)

app = FastAPI(
    title="AI Live Trading Bot Execution Service",
    version="0.1.0",
    docs_url="/docs",
)


class ConfirmationRequest(BaseModel):
    username: str = "demo"
    confirm: str = Field(min_length=1)


LiveArmRequest = ConfirmationRequest


class RunOnceRequest(BaseModel):
    username: str = "demo"
    symbol: str
    strategy: str


class ManualOrderRequest(ConfirmationRequest):
    symbol: str
    side: str = Field(pattern="^(BUY|SELL)$")
    volume: Decimal = Field(gt=0)
    stop_loss: Decimal
    take_profit: Decimal | None = None


class ClosePositionRequest(ConfirmationRequest):
    position_id: str


class BacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    strategy: str = "moving-average-crossover"


class AIRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fastapi", "time": timezone.now().isoformat()}


@app.get("/broker/status")
def broker_status() -> dict[str, Any]:
    settings = LiveTradingSettings.from_env()
    credentials = MT5LiveBroker().credentials
    return {
        "connected": False,
        "broker": "MT5",
        "credentials_configured": not credentials.missing_fields(),
        "missing_credentials": credentials.missing_fields(),
        "live_activation_errors": settings.activation_errors(),
    }


@app.post("/broker/connect")
def broker_connect() -> dict[str, Any]:
    broker = MT5LiveBroker()
    try:
        broker.connect()
        account = broker.get_account_info()
        return {
            "connected": True,
            "account_number": account.account_number,
            "server": account.server,
            "currency": account.currency,
            "trade_allowed": account.trade_allowed,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.post("/broker/disconnect")
def broker_disconnect() -> dict[str, str]:
    MT5LiveBroker().disconnect()
    return {"status": "disconnected"}


@app.get("/broker/account")
def broker_account() -> dict[str, Any]:
    account = BrokerAccount.objects.order_by("-last_sync_at").first()
    if account is None:
        raise HTTPException(status_code=404, detail="no account synced")
    return {
        "broker_name": account.broker_name,
        "account_number": account.account_number,
        "server": account.server,
        "currency": account.currency,
        "balance": str(account.balance),
        "equity": str(account.equity),
        "connected": account.connected,
        "trade_allowed": account.trade_allowed,
    }


@app.get("/broker/symbols/{symbol}")
def broker_symbol(symbol: str) -> dict[str, Any]:
    broker = MT5LiveBroker()
    try:
        broker.connect()
        info = broker.get_symbol_info(symbol)
        return _jsonable(asdict(info))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.get("/broker/tick/{symbol}")
def broker_tick(symbol: str) -> dict[str, Any]:
    broker = MT5LiveBroker()
    try:
        broker.connect()
        tick = broker.get_latest_tick(symbol)
        return _jsonable(asdict(tick))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.get("/broker/positions")
def broker_positions() -> list[dict[str, Any]]:
    return [
        {
            "id": position.id,
            "symbol": position.symbol.symbol,
            "side": position.side,
            "volume": str(position.volume),
            "status": position.status,
            "unrealized_pnl": str(position.unrealized_pnl),
        }
        for position in _position_queryset()
    ]


@app.get("/broker/orders")
def broker_orders() -> list[dict[str, Any]]:
    return [
        {
            "id": order.id,
            "symbol": order.symbol.symbol,
            "side": order.side,
            "status": order.status,
            "retcode": order.broker_retcode,
        }
        for order in LiveOrder.objects.order_by("-created_at")[:100]
    ]


@app.post("/bot/start")
def bot_start(request: ConfirmationRequest) -> dict[str, str]:
    _require_confirmation(request.confirm)
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.is_running = True
    state.save(update_fields=["is_running", "updated_at"])
    _audit(user, "BOT_STARTED", "WARNING", "Bot started through FastAPI.")
    return {"status": "running"}


@app.post("/bot/stop")
def bot_stop(request: ConfirmationRequest) -> dict[str, str]:
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.is_running = False
    state.save(update_fields=["is_running", "updated_at"])
    _audit(user, "BOT_STOPPED", "INFO", "Bot stopped through FastAPI.")
    return {"status": "stopped"}


@app.post("/bot/kill-switch")
def bot_kill_switch(request: ConfirmationRequest) -> dict[str, str]:
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.kill_switch_active = True
    state.is_running = False
    state.save(update_fields=["kill_switch_active", "is_running", "updated_at"])
    _audit(user, "KILL_SWITCH_ACTIVATED", "CRITICAL", "Kill switch activated through FastAPI.")
    return {"status": "kill_switch_active"}


@app.post("/bot/reset-kill-switch")
def reset_kill_switch(request: ConfirmationRequest) -> dict[str, str]:
    _require_confirmation(request.confirm)
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.kill_switch_active = False
    state.save(update_fields=["kill_switch_active", "updated_at"])
    _audit(user, "KILL_SWITCH_RESET", "WARNING", "Kill switch reset through FastAPI.")
    return {"status": "kill_switch_reset"}


@app.get("/bot/status")
def bot_status(username: str = "demo") -> dict[str, Any]:
    user = _user(username)
    state, _ = BotState.objects.get_or_create(user=user)
    return {
        "mode": state.mode,
        "is_running": state.is_running,
        "live_trading_armed": state.live_trading_armed,
        "kill_switch_active": state.kill_switch_active,
        "active_symbol": state.active_symbol.symbol if state.active_symbol else None,
        "active_strategy": state.active_strategy.slug if state.active_strategy else None,
    }


@app.post("/live/arm")
def live_arm(request: LiveArmRequest) -> dict[str, str]:
    _require_confirmation(request.confirm)
    settings = LiveTradingSettings.from_env()
    settings.assert_live_trading_allowed()
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.live_trading_armed = True
    state.mode = "LIVE"
    state.save(update_fields=["live_trading_armed", "mode", "updated_at"])
    _audit(user, "LIVE_TRADING_ARMED", "CRITICAL", "Live trading armed through FastAPI.")
    return {"status": "armed"}


@app.post("/live/disarm")
def live_disarm(request: ConfirmationRequest) -> dict[str, str]:
    user = _user(request.username)
    state, _ = BotState.objects.get_or_create(user=user)
    state.live_trading_armed = False
    state.is_running = False
    state.save(update_fields=["live_trading_armed", "is_running", "updated_at"])
    _audit(user, "LIVE_TRADING_DISARMED", "WARNING", "Live trading disarmed through FastAPI.")
    return {"status": "disarmed"}


@app.post("/live/run-once")
def live_run_once(request: RunOnceRequest) -> dict[str, Any]:
    from trading_engine.execution import LiveTradingEngine

    user = _user(request.username)
    symbol = TradingSymbol.objects.get(symbol=request.symbol)
    strategy = Strategy.objects.get(slug=request.strategy)
    broker = MT5LiveBroker()
    try:
        result = LiveTradingEngine(user=user, broker=broker).run_once(
            symbol=symbol,
            strategy_model=strategy,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        broker.disconnect()
    return {"status": result.status, "message": result.message, "order_id": result.order_id}


@app.post("/live/place-order")
def live_place_order(request: ManualOrderRequest) -> dict[str, Any]:
    _require_confirmation(request.confirm)
    LiveTradingSettings.from_env().assert_live_trading_allowed()
    broker = MT5LiveBroker()
    try:
        broker.connect()
        order_request = OrderRequest(
            symbol=request.symbol,
            side=cast(OrderSide, request.side),
            volume=request.volume,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )
        check = broker.check_order(order_request)
        if not check.ok:
            raise HTTPException(status_code=400, detail=f"order_check failed: {check.comment}")
        result = broker.place_market_order(order_request)
        return {"status": result.status, "retcode": result.retcode, "comment": result.comment}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.post("/live/close-position")
def live_close_position(request: ClosePositionRequest) -> dict[str, Any]:
    _require_confirmation(request.confirm)
    LiveTradingSettings.from_env().assert_live_trading_allowed()
    broker = MT5LiveBroker()
    try:
        broker.connect()
        result = broker.close_position(request.position_id)
        return {"status": result.status, "retcode": result.retcode, "comment": result.comment}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.post("/live/close-all-positions")
def live_close_all_positions(request: ConfirmationRequest) -> dict[str, Any]:
    _require_confirmation(request.confirm)
    LiveTradingSettings.from_env().assert_live_trading_allowed()
    broker = MT5LiveBroker()
    try:
        broker.connect()
        results = broker.close_all_positions()
        return {
            "closed": len(results),
            "results": [_jsonable(asdict(result)) for result in results],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        broker.disconnect()


@app.post("/backtests/run")
def backtest_run(request: BacktestRequest) -> dict[str, Any]:
    symbol = TradingSymbol.objects.get(symbol=request.symbol)
    strategy = Strategy.objects.get(slug=request.strategy)
    result = run_backtest(symbol=symbol, strategy_model=strategy)
    return {
        "id": result.id,
        "final_balance": str(result.final_balance),
        "return": str(result.total_return),
    }


@app.get("/backtests/{backtest_id}")
def backtest_detail(backtest_id: int) -> dict[str, Any]:
    from trading_engine.models import BacktestRun

    backtest = BacktestRun.objects.get(pk=backtest_id)
    return {
        "id": backtest.id,
        "symbol": backtest.symbol.symbol,
        "strategy": backtest.strategy.slug if backtest.strategy else None,
        "final_balance": str(backtest.final_balance),
        "total_return": str(backtest.total_return),
        "total_trades": backtest.total_trades,
    }


@app.get("/signals/recent")
def signals_recent() -> list[dict[str, Any]]:
    return [
        {
            "symbol": signal.symbol.symbol,
            "strategy": signal.strategy.slug,
            "type": signal.signal_type,
            "timestamp": signal.timestamp.isoformat(),
            "reason": signal.reason,
        }
        for signal in Signal.objects.order_by("-created_at")[:50]
    ]


@app.get("/risk/events")
def risk_events() -> list[dict[str, Any]]:
    return [
        {
            "event_type": event.event_type,
            "decision": event.decision,
            "triggered_rules": event.triggered_rules,
            "created_at": event.created_at.isoformat(),
        }
        for event in RiskEvent.objects.order_by("-created_at")[:100]
    ]


@app.post("/ai/signal-explanation")
def ai_signal_explanation(request: AIRequest) -> dict[str, str]:
    return {"content": get_ai_provider().explain_signal(request.payload)}


@app.post("/ai/trade-review")
def ai_trade_review(request: AIRequest) -> dict[str, str]:
    return {"content": get_ai_provider().review_trade(request.payload)}


def _require_confirmation(confirmation: str) -> None:
    if confirmation != CONFIRMATION_PHRASE:
        raise HTTPException(status_code=403, detail="incorrect confirmation phrase")


def _user(username: str):
    user, _ = get_user_model().objects.get_or_create(username=username)
    return user


def _audit(user, action: str, severity: str, description: str) -> None:
    AuditLog.objects.create(user=user, action=action, severity=severity, description=description)


def _position_queryset():
    from trading_engine.models import LivePosition

    return LivePosition.objects.order_by("-opened_at")[:100]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
