from __future__ import annotations

import importlib
from datetime import UTC, datetime
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
from trading_engine.brokers.exceptions import (
    BrokerConnectionError,
    BrokerCredentialsError,
    BrokerOrderError,
    BrokerSymbolError,
)
from trading_engine.configuration import MT5Credentials


class MT5LiveBroker(BaseBroker):
    """Live MetaTrader 5 broker adapter using the official MetaTrader5 module."""

    _TIMEFRAMES = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }

    def __init__(
        self,
        *,
        credentials: MT5Credentials | None = None,
        mt5_module: Any | None = None,
    ) -> None:
        self.credentials = credentials or MT5Credentials.from_env()
        self._mt5: Any = mt5_module
        self._connected = False

    def connect(self) -> None:
        missing = self.credentials.missing_fields()
        if missing:
            raise BrokerCredentialsError(
                "missing MT5 credential environment variables: " + ", ".join(missing)
            )
        mt5 = self._module()
        init_kwargs: dict[str, Any] = {"timeout": self.credentials.timeout_ms}
        if self.credentials.terminal_path is not None:
            init_kwargs["path"] = str(self.credentials.terminal_path)
        if not mt5.initialize(**init_kwargs):
            raise BrokerConnectionError(self._last_error_message("MT5 initialize failed"))
        if not mt5.login(
            self.credentials.login,
            password=self.credentials.password,
            server=self.credentials.server,
            timeout=self.credentials.timeout_ms,
        ):
            mt5.shutdown()
            raise BrokerConnectionError(self._last_error_message("MT5 login failed"))
        self._connected = True

    def disconnect(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_account_info(self) -> AccountInfo:
        self._require_connected()
        info = self._mt5.account_info()
        if info is None:
            raise BrokerConnectionError(self._last_error_message("MT5 account_info failed"))
        raw = _as_dict(info)
        return AccountInfo(
            account_number=str(raw.get("login", "")),
            server=str(raw.get("server", self.credentials.server)),
            currency=str(raw.get("currency", "")),
            balance=_decimal(raw.get("balance", "0")),
            equity=_decimal(raw.get("equity", "0")),
            margin=_decimal(raw.get("margin", "0")),
            free_margin=_decimal(raw.get("margin_free", "0")),
            leverage=_decimal(raw.get("leverage", "0")),
            trade_allowed=bool(raw.get("trade_allowed", False)),
            raw=raw,
        )

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._require_connected()
        raw_info = self._symbol_info_or_raise(symbol)
        raw = _as_dict(raw_info)
        trade_mode = int(raw.get("trade_mode", 0) or 0)
        tradeable = trade_mode != getattr(self._mt5, "SYMBOL_TRADE_MODE_DISABLED", 0)
        return SymbolInfo(
            symbol=str(raw.get("name", symbol)),
            tradeable=tradeable,
            visible=bool(raw.get("visible", False)),
            min_lot=_decimal(raw.get("volume_min", "0")),
            max_lot=_decimal(raw.get("volume_max", "0")),
            lot_step=_decimal(raw.get("volume_step", "0")),
            point=_decimal(raw.get("point", "0")),
            digits=int(raw.get("digits", 0) or 0),
            spread_points=_decimal(raw.get("spread", "0")),
            raw=raw,
        )

    def get_latest_tick(self, symbol: str) -> BrokerTick:
        self._require_connected()
        self._ensure_symbol_selected(symbol)
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise BrokerSymbolError(self._last_error_message(f"no latest tick for {symbol}"))
        raw = _as_dict(tick)
        timestamp = datetime.fromtimestamp(int(raw.get("time", 0) or 0), UTC)
        return BrokerTick(
            symbol=symbol,
            broker_time=timestamp,
            bid=_decimal(raw.get("bid", "0")),
            ask=_decimal(raw.get("ask", "0")),
            last=_decimal(raw.get("last", "0")),
            volume=_decimal(raw.get("volume", "0")),
            raw=raw,
        )

    def get_historical_rates(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        self._require_connected()
        self._ensure_symbol_selected(symbol)
        timeframe_value = self._timeframe_value(timeframe)
        rates = self._mt5.copy_rates_range(symbol, timeframe_value, start, end)
        if rates is None:
            raise BrokerConnectionError(self._last_error_message("copy_rates_range failed"))
        rows: list[dict[str, Any]] = []
        for rate in rates:
            raw = _as_dict(rate)
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": datetime.fromtimestamp(int(raw["time"]), UTC),
                    "open": _decimal(raw["open"]),
                    "high": _decimal(raw["high"]),
                    "low": _decimal(raw["low"]),
                    "close": _decimal(raw["close"]),
                    "volume": _decimal(raw.get("tick_volume", raw.get("real_volume", "0"))),
                    "raw": raw,
                }
            )
        return rows

    def get_open_positions(self, symbol: str | None = None) -> list[BrokerPosition]:
        self._require_connected()
        positions = self._mt5.positions_get(symbol=symbol) if symbol else self._mt5.positions_get()
        if positions is None:
            raise BrokerConnectionError(self._last_error_message("positions_get failed"))
        return [self._position_from_mt5(position) for position in positions]

    def get_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        self._require_connected()
        orders = self._mt5.orders_get(symbol=symbol) if symbol else self._mt5.orders_get()
        if orders is None:
            raise BrokerConnectionError(self._last_error_message("orders_get failed"))
        return [_as_dict(order) for order in orders]

    def calculate_margin(self, symbol: str, side: OrderSide, volume: Decimal) -> Decimal:
        self._require_connected()
        tick = self.get_latest_tick(symbol)
        order_type = self._order_type(side)
        price = tick.ask if side == "BUY" else tick.bid
        margin = self._mt5.order_calc_margin(order_type, symbol, float(volume), float(price))
        if margin is None:
            raise BrokerOrderError(self._last_error_message("order_calc_margin failed"))
        return _decimal(margin)

    def calculate_profit(
        self,
        symbol: str,
        side: OrderSide,
        volume: Decimal,
        entry_price: Decimal,
        exit_price: Decimal,
    ) -> Decimal:
        self._require_connected()
        profit = self._mt5.order_calc_profit(
            self._order_type(side),
            symbol,
            float(volume),
            float(entry_price),
            float(exit_price),
        )
        if profit is None:
            raise BrokerOrderError(self._last_error_message("order_calc_profit failed"))
        return _decimal(profit)

    def check_order(self, order_request: OrderRequest) -> OrderCheckResult:
        self._require_connected()
        order_request.validate()
        request = self.build_order_request(order_request)
        result = self._mt5.order_check(request)
        if result is None:
            return OrderCheckResult(
                ok=False, retcode=None, comment=self._last_error_message("order_check failed")
            )
        raw = _as_dict(result)
        retcode = int(raw.get("retcode", -1))
        ok = retcode in self._successful_check_retcodes()
        return OrderCheckResult(
            ok=ok,
            retcode=retcode,
            comment=str(raw.get("comment", "")),
            margin_required=_decimal(raw["margin"]) if "margin" in raw else None,
            raw=raw,
        )

    def place_market_order(self, order_request: OrderRequest) -> BrokerOrderResult:
        self._require_connected()
        order_request.validate()
        if order_request.order_type != "MARKET":
            raise BrokerOrderError("place_market_order only accepts MARKET requests")
        check = self.check_order(order_request)
        if not check.ok:
            return BrokerOrderResult(
                ok=False,
                status="REJECTED",
                retcode=check.retcode,
                comment=f"order_check rejected request: {check.comment}",
                raw=check.raw,
            )
        result = self._mt5.order_send(self.build_order_request(order_request))
        return self._order_result_from_mt5(result)

    def place_pending_order(self, order_request: OrderRequest) -> BrokerOrderResult:
        self._require_connected()
        order_request.validate()
        if order_request.order_type == "MARKET":
            raise BrokerOrderError("place_pending_order requires LIMIT or STOP order type")
        check = self.check_order(order_request)
        if not check.ok:
            return BrokerOrderResult(
                ok=False,
                status="REJECTED",
                retcode=check.retcode,
                comment=f"order_check rejected request: {check.comment}",
                raw=check.raw,
            )
        result = self._mt5.order_send(self.build_order_request(order_request))
        return self._order_result_from_mt5(result)

    def modify_position(
        self,
        position_id: str,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> BrokerOrderResult:
        self._require_connected()
        request = {
            "action": self._mt5.TRADE_ACTION_SLTP,
            "position": int(position_id),
            "sl": float(stop_loss) if stop_loss is not None else 0.0,
            "tp": float(take_profit) if take_profit is not None else 0.0,
            "magic": self.credentials.magic_number,
            "comment": "ai-live-trading-bot modify",
        }
        return self._order_result_from_mt5(self._mt5.order_send(request))

    def close_position(self, position_id: str) -> BrokerOrderResult:
        self._require_connected()
        position = self._find_position(position_id)
        tick = self.get_latest_tick(position.symbol)
        close_side: OrderSide = "SELL" if position.side == "BUY" else "BUY"
        price = tick.bid if close_side == "SELL" else tick.ask
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": self._order_type(close_side),
            "position": int(position.position_id),
            "price": float(price),
            "deviation": self.credentials.default_deviation_points,
            "magic": self.credentials.magic_number,
            "comment": "ai-live-trading-bot close",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        return self._order_result_from_mt5(self._mt5.order_send(request))

    def close_all_positions(self) -> list[BrokerOrderResult]:
        self._require_connected()
        return [self.close_position(position.position_id) for position in self.get_open_positions()]

    def sync_positions(self) -> list[BrokerPosition]:
        return self.get_open_positions()

    def sync_orders(self) -> list[dict[str, Any]]:
        return self.get_orders()

    def build_order_request(self, order_request: OrderRequest) -> dict[str, Any]:
        self._require_connected()
        self._ensure_symbol_selected(order_request.symbol)
        tick = self.get_latest_tick(order_request.symbol)
        if order_request.order_type == "MARKET":
            action = self._mt5.TRADE_ACTION_DEAL
            price = tick.ask if order_request.side == "BUY" else tick.bid
        else:
            action = self._mt5.TRADE_ACTION_PENDING
            if order_request.price is None:
                raise BrokerOrderError("pending orders require a requested price")
            price = order_request.price
        request = {
            "action": action,
            "symbol": order_request.symbol,
            "volume": float(order_request.volume),
            "type": self._order_type(order_request.side),
            "price": float(price),
            "sl": float(order_request.stop_loss) if order_request.stop_loss is not None else 0.0,
            "tp": (
                float(order_request.take_profit) if order_request.take_profit is not None else 0.0
            ),
            "deviation": order_request.deviation_points,
            "magic": order_request.magic_number,
            "comment": order_request.comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        return request

    def _module(self) -> Any:
        if self._mt5 is None:
            try:
                self._mt5 = importlib.import_module("MetaTrader5")
            except ImportError as exc:
                raise BrokerConnectionError(
                    "MetaTrader5 Python package is not installed in this environment"
                ) from exc
        return self._mt5

    def _require_connected(self) -> None:
        if not self._connected:
            raise BrokerConnectionError("MT5 broker is not connected")

    def _last_error_message(self, prefix: str) -> str:
        mt5 = self._module()
        try:
            code, message = mt5.last_error()
        except Exception:
            return prefix
        return f"{prefix}: {code} {message}"

    def _symbol_info_or_raise(self, symbol: str) -> Any:
        info = self._mt5.symbol_info(symbol)
        if info is None:
            raise BrokerSymbolError(self._last_error_message(f"symbol {symbol} not found"))
        return info

    def _ensure_symbol_selected(self, symbol: str) -> None:
        info = self._symbol_info_or_raise(symbol)
        raw = _as_dict(info)
        if not bool(raw.get("visible", False)) and not self._mt5.symbol_select(symbol, True):
            raise BrokerSymbolError(self._last_error_message(f"symbol {symbol} is not visible"))
        refreshed = self._symbol_info_or_raise(symbol)
        refreshed_raw = _as_dict(refreshed)
        trade_mode = int(refreshed_raw.get("trade_mode", 0) or 0)
        if trade_mode == getattr(self._mt5, "SYMBOL_TRADE_MODE_DISABLED", 0):
            raise BrokerSymbolError(f"symbol {symbol} is not tradeable")

    def _timeframe_value(self, timeframe: str) -> int:
        attr = self._TIMEFRAMES.get(timeframe.upper())
        if attr is None:
            raise ValueError(f"unsupported MT5 timeframe: {timeframe}")
        return int(getattr(self._mt5, attr))

    def _order_type(self, side: OrderSide) -> int:
        return int(getattr(self._mt5, "ORDER_TYPE_BUY" if side == "BUY" else "ORDER_TYPE_SELL"))

    def _successful_check_retcodes(self) -> set[int]:
        values = {0}
        for name in ("TRADE_RETCODE_DONE", "TRADE_RETCODE_PLACED", "TRADE_RETCODE_DONE_PARTIAL"):
            if hasattr(self._mt5, name):
                values.add(int(getattr(self._mt5, name)))
        return values

    def _order_result_from_mt5(self, result: Any) -> BrokerOrderResult:
        if result is None:
            return BrokerOrderResult(
                ok=False,
                status="FAILED",
                retcode=None,
                comment=self._last_error_message("order_send failed"),
            )
        raw = _as_dict(result)
        retcode = int(raw.get("retcode", -1))
        ok = retcode in self._successful_check_retcodes()
        status = "FILLED" if ok else "REJECTED"
        if retcode == getattr(self._mt5, "TRADE_RETCODE_DONE_PARTIAL", object()):
            status = "PARTIALLY_FILLED"
        return BrokerOrderResult(
            ok=ok,
            status=status,
            retcode=retcode,
            comment=str(raw.get("comment", "")),
            broker_order_id=str(raw.get("order", "")),
            broker_deal_id=str(raw.get("deal", "")),
            filled_volume=_decimal(raw.get("volume", "0")),
            filled_price=_decimal(raw["price"]) if raw.get("price") is not None else None,
            raw=raw,
        )

    def _position_from_mt5(self, position: Any) -> BrokerPosition:
        raw = _as_dict(position)
        position_type = int(raw.get("type", getattr(self._mt5, "POSITION_TYPE_BUY", 0)))
        side: OrderSide = (
            "BUY" if position_type == getattr(self._mt5, "POSITION_TYPE_BUY", 0) else "SELL"
        )
        return BrokerPosition(
            position_id=str(raw.get("ticket", "")),
            symbol=str(raw.get("symbol", "")),
            side=side,
            volume=_decimal(raw.get("volume", "0")),
            entry_price=_decimal(raw.get("price_open", "0")),
            current_price=_decimal(raw.get("price_current", "0")),
            stop_loss=_optional_decimal(raw.get("sl")),
            take_profit=_optional_decimal(raw.get("tp")),
            unrealized_pnl=_decimal(raw.get("profit", "0")),
            opened_at=datetime.fromtimestamp(int(raw.get("time", 0) or 0), UTC),
            raw=raw,
        )

    def _find_position(self, position_id: str) -> BrokerPosition:
        for position in self.get_open_positions():
            if position.position_id == position_id:
                return position
        raise BrokerOrderError(f"position {position_id} not found")


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "dtype") and hasattr(value, "item"):
        return {name: value[name].item() for name in value.dtype.names}
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return dict(value)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value in (None, "", 0, 0.0):
        return None
    return Decimal(str(value))
