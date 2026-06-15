from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from trading_engine.brokers import MT5LiveBroker
from trading_engine.execution import LiveTradingEngine
from trading_engine.models import AuditLog, BotState


@shared_task
def live_trading_loop_task(user_id: int) -> dict[str, str]:
    user = get_user_model().objects.get(pk=user_id)
    state, _ = BotState.objects.get_or_create(user=user)
    if state.kill_switch_active:
        return {"status": "blocked", "message": "kill switch active"}
    if state.active_symbol is None or state.active_strategy is None:
        return {"status": "blocked", "message": "active symbol/strategy missing"}
    state.last_heartbeat_at = timezone.now()
    state.save(update_fields=["last_heartbeat_at", "updated_at"])
    engine = LiveTradingEngine(user=user, broker=MT5LiveBroker())
    result = engine.run_once(symbol=state.active_symbol, strategy_model=state.active_strategy)
    return {"status": result.status, "message": result.message}


@shared_task
def sync_account_task() -> dict[str, str]:
    broker = MT5LiveBroker()
    try:
        broker.connect()
        for user in get_user_model().objects.filter(is_active=True):
            LiveTradingEngine(user=user, broker=broker).sync_account()
    finally:
        broker.disconnect()
    return {"status": "ok"}


@shared_task
def sync_positions_task() -> dict[str, str]:
    broker = MT5LiveBroker()
    try:
        broker.connect()
        for user in get_user_model().objects.filter(is_active=True):
            LiveTradingEngine(user=user, broker=broker).sync_positions()
    finally:
        broker.disconnect()
    return {"status": "ok"}


@shared_task
def generate_risk_summary_task(user_id: int) -> dict[str, str]:
    user = get_user_model().objects.get(pk=user_id)
    AuditLog.objects.create(
        user=user,
        action="RISK_SUMMARY_TASK",
        severity="INFO",
        description="Risk summary generation task executed.",
    )
    return {"status": "ok"}
