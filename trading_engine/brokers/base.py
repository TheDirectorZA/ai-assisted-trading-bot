from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT", "STOP"]


@dataclass(frozen=True, slots=True)
class AccountInfo:
    account_number: str
    server: str
    currency: str
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    leverage: Decimal
    trade_allowed: bool
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SymbolInfo:
    symbol: str
    tradeable: bool
    visible: bool
    min_lot: Decimal
    max_lot: Decimal
    lot_step: Decimal
    point: Decimal
    digits: int
    spread_points: Decimal
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BrokerTick:
    symbol: str
    broker_time: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal | None
    volume: Decimal
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    volume: Decimal
    order_type: OrderType = "MARKET"
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    deviation_points: int = 20
    comment: str = "ai-live-trading-bot"
    magic_number: int = 20260615

    def validate(self) -> None:
        if not self.symbol.strip():
            raise ValueError("order symbol is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("order side must be BUY or SELL")
        if self.order_type not in {"MARKET", "LIMIT", "STOP"}:
            raise ValueError("unsupported order type")
        if self.volume <= 0:
            raise ValueError("order volume must be greater than zero")
        if self.deviation_points < 0:
            raise ValueError("deviation points cannot be negative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "volume": str(self.volume),
            "order_type": self.order_type,
            "price": str(self.price) if self.price is not None else None,
            "stop_loss": str(self.stop_loss) if self.stop_loss is not None else None,
            "take_profit": str(self.take_profit) if self.take_profit is not None else None,
            "deviation_points": self.deviation_points,
            "comment": self.comment,
            "magic_number": self.magic_number,
        }


@dataclass(frozen=True, slots=True)
class OrderCheckResult:
    ok: bool
    retcode: int | None
    comment: str
    margin_required: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BrokerOrderResult:
    ok: bool
    status: str
    retcode: int | None
    comment: str
    broker_order_id: str = ""
    broker_deal_id: str = ""
    filled_volume: Decimal = Decimal("0")
    filled_price: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BrokerPosition:
    position_id: str
    symbol: str
    side: OrderSide
    volume: Decimal
    entry_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    unrealized_pnl: Decimal
    opened_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)


class BaseBroker(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def get_account_info(self) -> AccountInfo: ...

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> SymbolInfo: ...

    @abstractmethod
    def get_latest_tick(self, symbol: str) -> BrokerTick: ...

    @abstractmethod
    def get_historical_rates(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_open_positions(self, symbol: str | None = None) -> list[BrokerPosition]: ...

    @abstractmethod
    def get_orders(self, symbol: str | None = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    def calculate_margin(self, symbol: str, side: OrderSide, volume: Decimal) -> Decimal: ...

    @abstractmethod
    def calculate_profit(
        self,
        symbol: str,
        side: OrderSide,
        volume: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
    ) -> Decimal: ...

    @abstractmethod
    def check_order(self, order_request: OrderRequest) -> OrderCheckResult: ...

    @abstractmethod
    def place_market_order(self, order_request: OrderRequest) -> BrokerOrderResult: ...

    @abstractmethod
    def place_pending_order(self, order_request: OrderRequest) -> BrokerOrderResult: ...

    @abstractmethod
    def modify_position(
        self,
        position_id: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> BrokerOrderResult: ...

    @abstractmethod
    def close_position(self, position_id: str) -> BrokerOrderResult: ...

    @abstractmethod
    def close_all_positions(self) -> list[BrokerOrderResult]: ...

    @abstractmethod
    def sync_positions(self) -> list[BrokerPosition]: ...

    @abstractmethod
    def sync_orders(self) -> list[dict[str, Any]]: ...
