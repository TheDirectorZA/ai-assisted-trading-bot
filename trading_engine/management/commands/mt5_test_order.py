from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from trading_engine.brokers import MT5LiveBroker, OrderRequest
from trading_engine.configuration import REAL_ORDER_CONFIRMATION_PHRASE, LiveTradingSettings


class Command(BaseCommand):
    help = "Place a manual MT5 test order only with explicit real-money confirmation."

    def add_arguments(self, parser):
        parser.add_argument("--symbol", required=True)
        parser.add_argument("--volume", required=True)
        parser.add_argument("--side", choices=["BUY", "SELL"], default="BUY")
        parser.add_argument("--stop-loss", required=True)
        parser.add_argument("--take-profit")
        parser.add_argument("--confirm", required=True)

    def handle(self, *args, **options):
        if options["confirm"] != REAL_ORDER_CONFIRMATION_PHRASE:
            raise CommandError("incorrect confirmation phrase for real order test")
        LiveTradingSettings.from_env().assert_live_trading_allowed()
        broker = MT5LiveBroker()
        try:
            broker.connect()
            request = OrderRequest(
                symbol=options["symbol"],
                side=options["side"],
                volume=Decimal(options["volume"]),
                stop_loss=Decimal(options["stop_loss"]),
                take_profit=Decimal(options["take_profit"]) if options["take_profit"] else None,
            )
            result = broker.place_market_order(request)
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        finally:
            broker.disconnect()
        self.stdout.write(f"{result.status}: retcode={result.retcode} comment={result.comment}")
