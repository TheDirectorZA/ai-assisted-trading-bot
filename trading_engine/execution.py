from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from trading_engine.ai import AIProvider, get_ai_provider
from trading_engine.backtesting import strategy_from_model
from trading_engine.brokers.base import AccountInfo, BaseBroker, BrokerPosition, OrderRequest
from trading_engine.configuration import LiveTradingSettings, TradingMode
from trading_engine.market_data import persist_live_tick, price_jump_percentage
from trading_engine.models import (
    AuditLog,
    BotState,
    BrokerAccount,
    Candle,
    LiveOrder,
    LivePosition,
    OrderStatus,
    RiskSettings,
    Signal,
    Strategy,
    TradeJournalEntry,
    TradingSymbol,
)
from trading_engine.risk import (
    LiveTradeContext,
    RiskDecision,
    RiskManager,
    calculate_risk_based_volume,
)
from trading_engine.strategies import CandleData, StrategyContext


@dataclass(frozen=True, slots=True)
class EngineResult:
    status: str
    message: str
    risk_decision: RiskDecision | None = None
    order_id: int | None = None


class LiveTradingEngine:
    def __init__(
        self,
        *,
        user,
        broker: BaseBroker,
        ai_provider: AIProvider | None = None,
        settings: LiveTradingSettings | None = None,
    ) -> None:
        self.user = user
        self.broker = broker
        self.ai_provider = ai_provider or get_ai_provider()
        self.settings = settings or LiveTradingSettings.from_env()
        self.risk_manager = RiskManager()

    def run_once(self, *, symbol: TradingSymbol, strategy_model: Strategy) -> EngineResult:
        state, _ = BotState.objects.get_or_create(user=self.user)
        if state.kill_switch_active:
            self._audit("RUN_ONCE_BLOCKED_KILL_SWITCH", "CRITICAL", "Kill switch active.")
            return EngineResult("BLOCKED", "kill switch active")

        if not self.broker.is_connected():
            self.broker.connect()
        account_info = self.broker.get_account_info()
        broker_account = self.sync_account(account_info)
        self.sync_positions(broker_account)

        tick = self.broker.get_latest_tick(symbol.broker_symbol)
        persist_live_tick(symbol, tick)
        candles = self._load_candles(symbol)
        if len(candles) < 5:
            return EngineResult("NO_SIGNAL", "not enough candles")

        strategy = strategy_from_model(strategy_model)
        signal_payload = strategy.generate_signal(
            candles,
            StrategyContext(symbol=symbol.symbol, timeframe=symbol.timeframe),
        )
        signal = self._persist_signal(symbol, strategy_model, signal_payload)
        if signal is None:
            return EngineResult("BLOCKED", "duplicate signal already processed")
        if signal.signal_type == "HOLD":
            return EngineResult("NO_SIGNAL", signal.reason)

        stop_loss = strategy.calculate_stop_loss(
            signal_payload,
            candles,
            StrategyContext(symbol=symbol.symbol, timeframe=symbol.timeframe),
        )
        take_profit = strategy.calculate_take_profit(
            signal_payload,
            candles,
            StrategyContext(symbol=symbol.symbol, timeframe=symbol.timeframe),
        )
        symbol_info = self.broker.get_symbol_info(symbol.broker_symbol)
        try:
            volume = calculate_risk_based_volume(
                account_equity=account_info.equity,
                risk_percentage=self._risk_settings().max_risk_per_trade_percentage,
                entry_price=signal.price,
                stop_loss_price=stop_loss or signal.price,
                point=symbol.point,
                point_value_per_lot=Decimal("10"),
                lot_step=symbol.lot_step,
                min_lot=symbol.min_lot,
                max_lot=self._risk_settings().max_lot_size,
                broker_max_lot=symbol_info.max_lot,
            )
        except Exception as exc:
            self._audit("POSITION_SIZE_BLOCKED", "WARNING", str(exc))
            return EngineResult("BLOCKED", str(exc))

        order_request = OrderRequest(
            symbol=symbol.broker_symbol,
            side=signal.signal_type,
            volume=volume,
            price=signal.price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            deviation_points=int(self._risk_settings().max_slippage_points),
            magic_number=20260615,
        )
        order_check = self.broker.check_order(order_request)
        context = self._risk_context(
            symbol=symbol,
            strategy_model=strategy_model,
            account_info=account_info,
            symbol_info=symbol_info,
            order_request=order_request,
            order_check=order_check,
        )
        decision = self.risk_manager.evaluate(order_request, context)
        if not decision.approved:
            return EngineResult("BLOCKED", decision.reason, decision)

        live_order = LiveOrder.objects.create(
            user=self.user,
            broker_account=broker_account,
            symbol=symbol,
            strategy=strategy_model,
            signal=signal,
            side=signal.signal_type,
            order_type="MARKET",
            requested_volume=order_request.volume,
            requested_price=order_request.price,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
            deviation_points=order_request.deviation_points,
            status=OrderStatus.PRE_CHECKED,
            raw_request_json=order_request.as_dict(),
            raw_response_json=order_check.raw,
            broker_retcode=str(order_check.retcode or ""),
            broker_comment=order_check.comment,
        )
        self._audit(
            "LIVE_ORDER_PRECHECKED",
            "INFO",
            f"Order {live_order.id} pre-checked before execution.",
            {"order_id": live_order.id},
        )

        if self.settings.mode is not TradingMode.LIVE:
            live_order.status = OrderStatus.SENT
            live_order.broker_comment = "paper/forward mode: live order_send not called"
            live_order.save(update_fields=["status", "broker_comment"])
            return EngineResult(
                "PAPER_READY", "order passed risk checks in non-live mode", decision, live_order.id
            )

        self.settings.assert_live_trading_allowed()
        result = self.broker.place_market_order(order_request)
        live_order.raw_response_json = result.raw
        live_order.broker_retcode = str(result.retcode or "")
        live_order.broker_comment = result.comment
        live_order.broker_order_id = result.broker_order_id
        live_order.broker_deal_id = result.broker_deal_id
        live_order.filled_volume = result.filled_volume
        live_order.filled_price = result.filled_price
        live_order.status = result.status
        if result.ok:
            live_order.filled_at = timezone.now()
        live_order.save()
        self.sync_positions(broker_account)
        TradeJournalEntry.objects.create(
            user=self.user,
            symbol=symbol,
            strategy=strategy_model,
            mode="LIVE",
            related_order=live_order,
            title=f"Live order {live_order.id}",
            notes=self.ai_provider.explain_signal(asdict(signal_payload)),
        )
        self._audit(
            "LIVE_ORDER_SENT",
            "CRITICAL" if result.ok else "ERROR",
            f"Broker returned {result.status}: {result.comment}",
            {"order_id": live_order.id, "retcode": result.retcode},
        )
        return EngineResult(result.status, result.comment, decision, live_order.id)

    def sync_account(self, account_info: AccountInfo | None = None) -> BrokerAccount:
        info = account_info or self.broker.get_account_info()
        account, _ = BrokerAccount.objects.update_or_create(
            user=self.user,
            broker_name="MT5" if info.server != "mock" else "MOCK",
            account_number=info.account_number,
            defaults={
                "server": info.server,
                "currency": info.currency,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.free_margin,
                "leverage": info.leverage,
                "trade_allowed": info.trade_allowed,
                "connected": self.broker.is_connected(),
                "last_sync_at": timezone.now(),
            },
        )
        return account

    def sync_positions(self, broker_account: BrokerAccount | None = None) -> list[LivePosition]:
        account = broker_account or self.sync_account()
        synced: list[LivePosition] = []
        for broker_position in self.broker.sync_positions():
            symbol, _ = TradingSymbol.objects.get_or_create(
                symbol=broker_position.symbol,
                defaults={"broker_symbol": broker_position.symbol},
            )
            position = self._upsert_position(account, symbol, broker_position)
            synced.append(position)
        return synced

    def _risk_context(
        self,
        *,
        symbol: TradingSymbol,
        strategy_model: Strategy,
        account_info: AccountInfo,
        symbol_info,
        order_request: OrderRequest,
        order_check,
    ) -> LiveTradeContext:
        tick = self.broker.get_latest_tick(symbol.broker_symbol)
        candles = Candle.objects.filter(symbol=symbol, timeframe=symbol.timeframe).order_by(
            "-timestamp"
        )[:2]
        latest_candle = candles[0] if candles else None
        previous_candle = candles[1] if len(candles) > 1 else latest_candle
        tick_age = int((timezone.now() - tick.broker_time).total_seconds())
        candle_age = (
            int((timezone.now() - latest_candle.timestamp).total_seconds())
            if latest_candle is not None
            else self.settings.max_candle_age_seconds + 1
        )
        jump = (
            price_jump_percentage(previous_candle.close, latest_candle.close)
            if previous_candle is not None and latest_candle is not None
            else Decimal("0")
        )
        open_positions = LivePosition.objects.filter(user=self.user, status="OPEN")
        return LiveTradeContext(
            mode=self.settings.mode,
            settings=self.settings,
            risk_settings=self._risk_settings(),
            user=self.user,
            django_symbol=symbol,
            django_strategy=strategy_model,
            account=account_info,
            symbol_info=symbol_info,
            latest_tick=tick,
            tick_age_seconds=max(tick_age, 0),
            candle_age_seconds=max(candle_age, 0),
            spread_points=(tick.ask - tick.bid) / symbol.point,
            price_jump_percentage=jump,
            open_positions_count=open_positions.count(),
            open_positions_for_symbol=open_positions.filter(symbol=symbol).count(),
            daily_loss_percentage=Decimal("0"),
            weekly_loss_percentage=Decimal("0"),
            consecutive_losses=0,
            current_leverage=account_info.leverage,
            margin_required=order_check.margin_required or Decimal("0"),
            duplicate_signal=False,
            broker_connected=self.broker.is_connected(),
            order_check=order_check,
        )

    def _load_candles(self, symbol: TradingSymbol) -> list[CandleData]:
        return [
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

    def _persist_signal(
        self, symbol: TradingSymbol, strategy: Strategy, signal_payload
    ) -> Signal | None:
        try:
            return Signal.objects.create(
                symbol=symbol,
                strategy=strategy,
                timestamp=signal_payload.timestamp,
                timeframe=symbol.timeframe,
                signal_type=signal_payload.signal_type,
                price=signal_payload.price,
                confidence=signal_payload.confidence,
                reason=signal_payload.reason,
                mode=self.settings.mode.value.upper(),
            )
        except IntegrityError:
            return None

    def _risk_settings(self) -> RiskSettings:
        risk_settings, _ = RiskSettings.objects.get_or_create(user=self.user)
        return risk_settings

    def _upsert_position(
        self,
        account: BrokerAccount,
        symbol: TradingSymbol,
        broker_position: BrokerPosition,
    ) -> LivePosition:
        position, _ = LivePosition.objects.update_or_create(
            user=self.user,
            broker_account=account,
            broker_position_id=broker_position.position_id,
            defaults={
                "symbol": symbol,
                "side": broker_position.side,
                "volume": broker_position.volume,
                "entry_price": broker_position.entry_price,
                "current_price": broker_position.current_price,
                "stop_loss": broker_position.stop_loss,
                "take_profit": broker_position.take_profit,
                "unrealized_pnl": broker_position.unrealized_pnl,
                "opened_at": broker_position.opened_at,
                "last_sync_at": timezone.now(),
                "status": "OPEN",
            },
        )
        return position

    def _audit(
        self,
        action: str,
        severity: str,
        description: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        AuditLog.objects.create(
            user=self.user,
            action=action,
            severity=severity,
            description=description,
            metadata=metadata or {},
        )
