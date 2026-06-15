from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from trading_engine.brokers.base import (
    AccountInfo,
    BaseBroker,
    BrokerOrderResult,
    BrokerPosition,
    BrokerTick,
    OrderCheckResult,
    OrderRequest,
    OrderSide,
    SymbolInfo,
)
from trading_engine.brokers.exceptions import BrokerConnectionError, BrokerOrderError


class MockBroker(BaseBroker):
    """Deterministic local broker used for tests and safe development."""

    def __init__(self) -> None:
        self._connected = False
        self._positions: list[BrokerPosition] = []
        self._orders: list[dict[str, Any]] = []
        self._next_id = 1

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_account_info(self) -> AccountInfo:
        self._require_connected()
        return AccountInfo(
            account_number="MOCK-001",
            server="mock",
            currency="USD",
            balance=Decimal("10000.00"),
            equity=Decimal("10000.00"),
            margin=Decimal("0.00"),
            free_margin=Decimal("10000.00"),
            leverage=Decimal("30"),
            trade_allowed=True,
        )

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._require_connected()
        return SymbolInfo(
            symbol=symbol.upper(),
            tradeable=True,
            visible=True,
            min_lot=Decimal("0.01"),
            max_lot=Decimal("100"),
            lot_step=Decimal("0.01"),
            point=Decimal("0.0001"),
            digits=5,
            spread_points=Decimal("10"),
        )

    def get_latest_tick(self, symbol: str) -> BrokerTick:
        self._require_connected()
        return BrokerTick(
            symbol=symbol.upper(),
            broker_time=datetime.now(UTC),
            bid=Decimal("1.10000"),
            ask=Decimal("1.10100"),
            last=Decimal("1.10050"),
            volume=Decimal("1000"),
        )

    def get_historical_rates(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        self._require_connected()
        rows: list[dict[str, Any]] = []
        cursor = start
        price = Decimal("1.10000")
        while cursor <= end:
            close = price + Decimal("0.00010")
            rows.append(
                {
                    "symbol": symbol.upper(),
                    "timeframe": timeframe,
                    "timestamp": cursor,
                    "open": price,
                    "high": close + Decimal("0.00020"),
                    "low": price - Decimal("0.00020"),
                    "close": close,
                    "volume": Decimal("1000"),
                }
            )
            price = close
            cursor += timedelta(minutes=5)
        return rows

    def get_open_positions(self, symbol: str | None = None) -> list[BrokerPosition]:
        self._require_connected()
        if symbol is None:
            return list(self._positions)
        normalized = symbol.upper()
        return [position for position in self._positions if position.symbol == normalized]

    def get_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        self._require_connected()
        if symbol is None:
            return list(self._orders)
        normalized = symbol.upper()
        return [order for order in self._orders if order.get("symbol") == normalized]

    def calculate_margin(self, symbol: str, side: OrderSide, volume: Decimal) -> Decimal:
        self._require_connected()
        return (volume * Decimal("1000")).quantize(Decimal("0.01"))

    def calculate_profit(
        self,
        symbol: str,
        side: OrderSide,
        volume: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
    ) -> Decimal:
        multiplier = Decimal("100000")
        direction = Decimal("1") if side == "BUY" else Decimal("-1")
        return ((exit_price - entry_price) * volume * multiplier * direction).quantize(
            Decimal("0.01")
        )

    def check_order(self, order_request: OrderRequest) -> OrderCheckResult:
        self._require_connected()
        try:
            order_request.validate()
        except ValueError as exc:
            return OrderCheckResult(ok=False, retcode=None, comment=str(exc))
        if order_request.stop_loss is None:
            return OrderCheckResult(ok=False, retcode=None, comment="stop loss is required")
        return OrderCheckResult(ok=True, retcode=0, comment="mock order check passed")

    def place_market_order(self, order_request: OrderRequest) -> BrokerOrderResult:
        self._require_connected()
        check = self.check_order(order_request)
        if not check.ok:
            raise BrokerOrderError(check.comment)
        tick = self.get_latest_tick(order_request.symbol)
        price = tick.ask if order_request.side == "BUY" else tick.bid
        order_id = str(self._next_id)
        self._next_id += 1
        position = BrokerPosition(
            position_id=order_id,
            symbol=order_request.symbol.upper(),
            side=order_request.side,
            volume=order_request.volume,
            entry_price=price,
            current_price=price,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
            unrealized_pnl=Decimal("0"),
            opened_at=datetime.now(UTC),
        )
        self._positions.append(position)
        raw_order = order_request.as_dict() | {"order_id": order_id}
        self._orders.append(raw_order)
        return BrokerOrderResult(
            ok=True,
            status="FILLED",
            retcode=0,
            comment="mock market order filled",
            broker_order_id=order_id,
            broker_deal_id=order_id,
            filled_volume=order_request.volume,
            filled_price=price,
            raw=raw_order,
        )

    def place_pending_order(self, order_request: OrderRequest) -> BrokerOrderResult:
        self._require_connected()
        check = self.check_order(order_request)
        if not check.ok:
            raise BrokerOrderError(check.comment)
        order_id = str(self._next_id)
        self._next_id += 1
        raw_order = order_request.as_dict() | {"order_id": order_id, "status": "PENDING"}
        self._orders.append(raw_order)
        return BrokerOrderResult(
            ok=True,
            status="SENT",
            retcode=0,
            comment="mock pending order accepted",
            broker_order_id=order_id,
            raw=raw_order,
        )

    def modify_position(
        self,
        position_id: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> BrokerOrderResult:
        self._require_connected()
        for index, position in enumerate(self._positions):
            if position.position_id == position_id:
                updated = BrokerPosition(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    side=position.side,
                    volume=position.volume,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    stop_loss=stop_loss if stop_loss is not None else position.stop_loss,
                    take_profit=take_profit if take_profit is not None else position.take_profit,
                    unrealized_pnl=position.unrealized_pnl,
                    opened_at=position.opened_at,
                    raw=position.raw,
                )
                self._positions[index] = updated
                return BrokerOrderResult(
                    ok=True, status="MODIFIED", retcode=0, comment="position modified"
                )
        return BrokerOrderResult(
            ok=False, status="FAILED", retcode=None, comment="position not found"
        )

    def close_position(self, position_id: str) -> BrokerOrderResult:
        self._require_connected()
        before = len(self._positions)
        self._positions = [
            position for position in self._positions if position.position_id != position_id
        ]
        if len(self._positions) == before:
            return BrokerOrderResult(
                ok=False, status="FAILED", retcode=None, comment="position not found"
            )
        return BrokerOrderResult(
            ok=True,
            status="CLOSED",
            retcode=0,
            comment="position closed",
            broker_order_id=position_id,
        )

    def close_all_positions(self) -> list[BrokerOrderResult]:
        self._require_connected()
        ids = [position.position_id for position in self._positions]
        return [self.close_position(position_id) for position_id in ids]

    def sync_positions(self) -> list[BrokerPosition]:
        return self.get_open_positions()

    def sync_orders(self) -> list[dict[str, Any]]:
        return self.get_orders()

    def _require_connected(self) -> None:
        if not self._connected:
            raise BrokerConnectionError("broker is not connected")
