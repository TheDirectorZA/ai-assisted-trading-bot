from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal
from typing import Any

from django.utils import timezone

from trading_engine.brokers.base import (
    AccountInfo,
    BrokerTick,
    OrderCheckResult,
    OrderRequest,
    SymbolInfo,
)
from trading_engine.configuration import LiveTradingSettings, TradingMode


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: str
    triggered_rules: list[str] = field(default_factory=list)
    original_position_size: Decimal = Decimal("0")
    adjusted_position_size: Decimal = Decimal("0")
    max_allowed_loss: Decimal = Decimal("0")
    expected_loss_at_stop: Decimal = Decimal("0")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LiveTradeContext:
    mode: TradingMode
    settings: LiveTradingSettings
    risk_settings: Any
    user: Any | None
    django_symbol: Any | None
    django_strategy: Any | None
    account: AccountInfo
    symbol_info: SymbolInfo
    latest_tick: BrokerTick
    tick_age_seconds: int
    candle_age_seconds: int
    spread_points: Decimal
    price_jump_percentage: Decimal
    open_positions_count: int
    open_positions_for_symbol: int
    daily_loss_percentage: Decimal
    weekly_loss_percentage: Decimal
    consecutive_losses: int
    current_leverage: Decimal
    margin_required: Decimal
    duplicate_signal: bool
    broker_connected: bool
    order_check: OrderCheckResult | None
    now_time: time | None = None


class RiskManager:
    def evaluate(self, order: OrderRequest, context: LiveTradeContext) -> RiskDecision:
        order.validate()
        triggered: list[str] = []
        metadata: dict[str, Any] = {}
        risk_settings = context.risk_settings
        max_allowed_loss = context.account.equity * (
            Decimal(str(risk_settings.max_risk_per_trade_percentage)) / Decimal("100")
        )
        expected_loss = self._expected_loss(order, context)

        if context.mode is TradingMode.LIVE:
            triggered.extend(context.settings.activation_errors())
        if not context.broker_connected:
            triggered.append("broker is not connected")
        if not context.account.trade_allowed:
            triggered.append("broker account trade_allowed is false")
        if self._is_kill_switch_active(context):
            triggered.append("kill switch is active")
        if context.django_symbol is not None:
            if not context.django_symbol.is_active:
                triggered.append("symbol is inactive")
            if context.mode is TradingMode.LIVE and not context.django_symbol.is_live_enabled:
                triggered.append("symbol is not live enabled")
        if context.django_strategy is not None:
            if not context.django_strategy.is_active:
                triggered.append("strategy is inactive")
            if context.mode is TradingMode.LIVE and not context.django_strategy.is_live_enabled:
                triggered.append("strategy is not live enabled")
        if not context.symbol_info.tradeable:
            triggered.append("symbol is not tradeable")
        if context.spread_points > Decimal(str(risk_settings.max_spread_points)):
            triggered.append("spread exceeds risk setting")
        if (
            context.spread_points > context.symbol_info.spread_points
            and context.symbol_info.spread_points > 0
        ):
            metadata["broker_spread_points"] = str(context.symbol_info.spread_points)
        if context.tick_age_seconds > int(risk_settings.stale_data_threshold_seconds):
            triggered.append("live tick data is stale")
        if context.candle_age_seconds > context.settings.max_candle_age_seconds:
            triggered.append("candle data is stale")
        if context.price_jump_percentage > Decimal(str(risk_settings.max_price_jump_percentage)):
            triggered.append("price jump exceeds limit")
        if risk_settings.require_stop_loss and order.stop_loss is None:
            triggered.append("stop loss is required")
        if risk_settings.require_take_profit and order.take_profit is None:
            triggered.append("take profit is required")
        if order.stop_loss is not None:
            stop_points = self._stop_distance_points(order, context)
            if stop_points < Decimal(str(risk_settings.min_stop_loss_points)):
                triggered.append("stop loss distance is below minimum")
            if stop_points > Decimal(str(risk_settings.max_stop_loss_points)):
                triggered.append("stop loss distance exceeds maximum")
            if expected_loss > max_allowed_loss:
                triggered.append("expected loss at stop exceeds risk per trade")
        if order.volume <= 0:
            triggered.append("position size is invalid")
        if order.volume > Decimal(str(risk_settings.max_lot_size)):
            triggered.append("position size exceeds max lot size")
        if order.volume > context.symbol_info.max_lot:
            triggered.append("position size exceeds broker max lot")
        if order.volume < context.symbol_info.min_lot:
            triggered.append("position size below broker min lot")
        if context.open_positions_count >= int(risk_settings.max_open_positions):
            triggered.append("max open positions reached")
        if context.open_positions_for_symbol >= int(risk_settings.max_positions_per_symbol):
            triggered.append("max positions per symbol reached")
        if context.daily_loss_percentage >= Decimal(str(risk_settings.max_daily_loss_percentage)):
            triggered.append("daily loss limit reached")
        if context.weekly_loss_percentage >= Decimal(str(risk_settings.max_weekly_loss_percentage)):
            triggered.append("weekly loss limit reached")
        if context.current_leverage > Decimal(str(risk_settings.max_leverage)):
            triggered.append("max leverage exceeded")
        if context.margin_required > context.account.free_margin:
            triggered.append("insufficient free margin")
        if context.consecutive_losses >= int(risk_settings.stop_trading_after_losses):
            triggered.append("consecutive loss limit reached")
        if self._outside_trading_hours(context):
            triggered.append("outside allowed trading hours")
        if self._symbol_not_allowed(order, risk_settings):
            triggered.append("symbol is not in allowed symbols")
        if context.duplicate_signal:
            triggered.append("duplicate signal already processed")
        if context.order_check is None:
            triggered.append("broker order_check was not run")
        elif not context.order_check.ok:
            triggered.append(f"broker order_check failed: {context.order_check.comment}")

        if triggered:
            decision = RiskDecision(
                approved=False,
                reason="; ".join(triggered),
                triggered_rules=triggered,
                original_position_size=order.volume,
                adjusted_position_size=Decimal("0"),
                max_allowed_loss=max_allowed_loss,
                expected_loss_at_stop=expected_loss,
                metadata=metadata,
            )
            self._record_blocked_trade(decision, context)
            return decision

        return RiskDecision(
            approved=True,
            reason="risk checks approved",
            original_position_size=order.volume,
            adjusted_position_size=order.volume,
            max_allowed_loss=max_allowed_loss,
            expected_loss_at_stop=expected_loss,
            metadata=metadata,
        )

    def _expected_loss(self, order: OrderRequest, context: LiveTradeContext) -> Decimal:
        if order.stop_loss is None:
            return Decimal("0")
        stop_points = self._stop_distance_points(order, context)
        point_value_per_lot = Decimal("10")
        return (stop_points * point_value_per_lot * order.volume).quantize(Decimal("0.01"))

    def _stop_distance_points(self, order: OrderRequest, context: LiveTradeContext) -> Decimal:
        if order.stop_loss is None:
            return Decimal("0")
        entry = order.price
        if entry is None:
            entry = context.latest_tick.ask if order.side == "BUY" else context.latest_tick.bid
        return (abs(entry - order.stop_loss) / context.symbol_info.point).quantize(
            Decimal("0.0001")
        )

    def _is_kill_switch_active(self, context: LiveTradeContext) -> bool:
        if context.user is None:
            return False
        try:
            from trading_engine.models import BotState

            return BotState.objects.filter(user=context.user, kill_switch_active=True).exists()
        except Exception:
            return False

    def _outside_trading_hours(self, context: LiveTradeContext) -> bool:
        start = context.risk_settings.trading_start_time
        end = context.risk_settings.trading_end_time
        if start is None or end is None:
            return False
        current = context.now_time or timezone.localtime().time()
        if start <= end:
            return not (start <= current <= end)
        return not (current >= start or current <= end)

    def _symbol_not_allowed(self, order: OrderRequest, risk_settings: Any) -> bool:
        allowed_symbols = risk_settings.allowed_symbols or []
        return bool(allowed_symbols) and order.symbol not in allowed_symbols

    def _record_blocked_trade(self, decision: RiskDecision, context: LiveTradeContext) -> None:
        try:
            from trading_engine.models import AuditLog, RiskEvent

            RiskEvent.objects.create(
                user=context.user,
                symbol=context.django_symbol,
                strategy=context.django_strategy,
                event_type="TRADE_BLOCKED",
                severity="WARNING",
                decision="BLOCKED",
                triggered_rules=decision.triggered_rules,
                description=decision.reason,
                metadata=decision.metadata,
            )
            AuditLog.objects.create(
                user=context.user,
                action="TRADE_BLOCKED_BY_RISK_MANAGER",
                severity="WARNING",
                description=decision.reason,
                metadata={"triggered_rules": decision.triggered_rules},
            )
        except Exception:
            return
