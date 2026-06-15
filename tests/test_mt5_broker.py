from __future__ import annotations

from collections import namedtuple
from decimal import Decimal

import pytest

from trading_engine.brokers import MT5LiveBroker, OrderRequest
from trading_engine.brokers.exceptions import BrokerCredentialsError
from trading_engine.configuration import MT5Credentials


class FakeMT5:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 0
    POSITION_TYPE_BUY = 0
    SYMBOL_TRADE_MODE_DISABLED = 0
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_PLACED = 10008
    TIMEFRAME_M5 = 5

    def __init__(self) -> None:
        self.last_request = None
        self.shutdown_called = False

    def initialize(self, **kwargs):
        return True

    def login(self, login, password, server, timeout):
        return True

    def shutdown(self):
        self.shutdown_called = True

    def last_error(self):
        return (0, "ok")

    def account_info(self):
        Row = namedtuple(
            "AccountInfo",
            "login server currency balance equity margin margin_free leverage trade_allowed",
        )
        return Row(123, "demo-server", "USD", 10000, 10000, 0, 10000, 30, True)

    def symbol_info(self, symbol):
        Row = namedtuple(
            "SymbolInfo",
            "name visible trade_mode volume_min volume_max volume_step point digits spread",
        )
        return Row(symbol, True, 1, 0.01, 100, 0.01, 0.0001, 5, 10)

    def symbol_select(self, symbol, enabled):
        return True

    def symbol_info_tick(self, symbol):
        Row = namedtuple("Tick", "time bid ask last volume")
        return Row(1_700_000_000, 1.1000, 1.1010, 1.1005, 1000)

    def order_check(self, request):
        self.last_request = request
        Row = namedtuple("Check", "retcode comment margin")
        return Row(self.TRADE_RETCODE_DONE, "check ok", 12.5)

    def order_send(self, request):
        self.last_request = request
        Row = namedtuple("Result", "retcode comment order deal volume price")
        return Row(self.TRADE_RETCODE_DONE, "filled", 777, 888, request["volume"], request["price"])

    def positions_get(self, symbol=None):
        return []

    def orders_get(self, symbol=None):
        return []

    def order_calc_margin(self, order_type, symbol, volume, price):
        return 12.5

    def order_calc_profit(self, order_type, symbol, volume, entry, exit):
        return 10.0


def credentials() -> MT5Credentials:
    return MT5Credentials(
        login=123,
        password="test-password",
        server="demo-server",
        terminal_path=None,
        timeout_ms=60000,
        magic_number=20260615,
        default_deviation_points=20,
    )


def test_mt5_adapter_missing_credentials_fails_safely() -> None:
    broker = MT5LiveBroker(
        credentials=MT5Credentials(
            login=None,
            password="",
            server="",
            terminal_path=None,
            timeout_ms=60000,
            magic_number=20260615,
            default_deviation_points=20,
        ),
        mt5_module=FakeMT5(),
    )

    with pytest.raises(BrokerCredentialsError):
        broker.connect()


def test_mt5_adapter_builds_checks_and_sends_order() -> None:
    fake = FakeMT5()
    broker = MT5LiveBroker(credentials=credentials(), mt5_module=fake)
    broker.connect()
    request = OrderRequest(
        symbol="EURUSD",
        side="BUY",
        volume=Decimal("0.01"),
        stop_loss=Decimal("1.0900"),
        take_profit=Decimal("1.1200"),
    )

    check = broker.check_order(request)
    result = broker.place_market_order(request)

    assert check.ok is True
    assert result.ok is True
    assert fake.last_request["symbol"] == "EURUSD"
    assert fake.last_request["sl"] == 1.09
