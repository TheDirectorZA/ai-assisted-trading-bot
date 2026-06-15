from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from trading_engine.brokers import (
    AccountInfo,
    BrokerTick,
    OrderCheckResult,
    OrderRequest,
    SymbolInfo,
)
from trading_engine.configuration import LiveTradingSettings, TradingMode
from trading_engine.models import BotState, RiskSettings, Strategy, TradingSymbol
from trading_engine.risk import LiveTradeContext, RiskManager


@pytest.fixture
def risk_objects(db):
    user = get_user_model().objects.create_user(username="risk-user")
    symbol = TradingSymbol.objects.create(
        symbol="EURUSD",
        broker_symbol="EURUSD",
        is_live_enabled=True,
    )
    strategy = Strategy.objects.create(
        name="Moving Average",
        slug="moving-average-crossover",
        strategy_type="technical",
        is_live_enabled=True,
    )
    risk_settings = RiskSettings.objects.create(user=user)
    return user, symbol, strategy, risk_settings


def _context(user, symbol, strategy, risk_settings) -> LiveTradeContext:
    settings = LiveTradingSettings(
        mode=TradingMode.PAPER,
        live_trading_enabled=False,
        live_trading_armed=False,
        confirmation_phrase="",
        max_tick_age_seconds=10,
        max_candle_age_seconds=120,
        max_order_failures=3,
        close_positions_on_kill_switch=False,
        ai_provider="mock",
        ollama_base_url="http://localhost:11434",
        ollama_model="",
    )
    return LiveTradeContext(
        mode=TradingMode.PAPER,
        settings=settings,
        risk_settings=risk_settings,
        user=user,
        django_symbol=symbol,
        django_strategy=strategy,
        account=AccountInfo(
            account_number="1",
            server="demo",
            currency="USD",
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            margin=Decimal("0"),
            free_margin=Decimal("10000"),
            leverage=Decimal("10"),
            trade_allowed=True,
        ),
        symbol_info=SymbolInfo(
            symbol="EURUSD",
            tradeable=True,
            visible=True,
            min_lot=Decimal("0.01"),
            max_lot=Decimal("100"),
            lot_step=Decimal("0.01"),
            point=Decimal("0.0001"),
            digits=5,
            spread_points=Decimal("10"),
        ),
        latest_tick=BrokerTick(
            symbol="EURUSD",
            broker_time=datetime.now(UTC),
            bid=Decimal("1.1000"),
            ask=Decimal("1.1010"),
            last=Decimal("1.1005"),
            volume=Decimal("1000"),
        ),
        tick_age_seconds=1,
        candle_age_seconds=10,
        spread_points=Decimal("10"),
        price_jump_percentage=Decimal("0.1"),
        open_positions_count=0,
        open_positions_for_symbol=0,
        daily_loss_percentage=Decimal("0"),
        weekly_loss_percentage=Decimal("0"),
        consecutive_losses=0,
        current_leverage=Decimal("10"),
        margin_required=Decimal("10"),
        duplicate_signal=False,
        broker_connected=True,
        order_check=OrderCheckResult(ok=True, retcode=0, comment="ok"),
    )


def _order() -> OrderRequest:
    return OrderRequest(
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("0.10"),
        price=Decimal("1.1010"),
        stop_loss=Decimal("1.0910"),
        take_profit=Decimal("1.1210"),
    )


@pytest.mark.django_db
def test_risk_manager_approves_safe_trade(risk_objects) -> None:
    user, symbol, strategy, risk_settings = risk_objects

    decision = RiskManager().evaluate(_order(), _context(user, symbol, strategy, risk_settings))

    assert decision.approved is True


@pytest.mark.django_db
def test_risk_manager_blocks_kill_switch(risk_objects) -> None:
    user, symbol, strategy, risk_settings = risk_objects
    BotState.objects.create(user=user, kill_switch_active=True)

    decision = RiskManager().evaluate(_order(), _context(user, symbol, strategy, risk_settings))

    assert decision.approved is False
    assert "kill switch is active" in decision.triggered_rules


@pytest.mark.django_db
def test_risk_manager_blocks_spread_and_stale_data(risk_objects) -> None:
    user, symbol, strategy, risk_settings = risk_objects
    context = replace(
        _context(user, symbol, strategy, risk_settings),
        spread_points=Decimal("100"),
        tick_age_seconds=999,
    )

    decision = RiskManager().evaluate(_order(), context)

    assert "spread exceeds risk setting" in decision.triggered_rules
    assert "live tick data is stale" in decision.triggered_rules


@pytest.mark.django_db
def test_risk_manager_blocks_duplicate_and_daily_loss(risk_objects) -> None:
    user, symbol, strategy, risk_settings = risk_objects
    context = replace(
        _context(user, symbol, strategy, risk_settings),
        duplicate_signal=True,
        daily_loss_percentage=Decimal("4"),
    )

    decision = RiskManager().evaluate(_order(), context)

    assert "duplicate signal already processed" in decision.triggered_rules
    assert "daily loss limit reached" in decision.triggered_rules
