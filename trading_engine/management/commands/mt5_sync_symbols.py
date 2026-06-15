from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from trading_engine.brokers import MT5LiveBroker
from trading_engine.models import TradingSymbol


class Command(BaseCommand):
    help = "Sync one or more configured symbols from MT5."

    def add_arguments(self, parser):
        parser.add_argument("symbols", nargs="+")

    def handle(self, *args, **options):
        broker = MT5LiveBroker()
        try:
            broker.connect()
            for symbol_name in options["symbols"]:
                info = broker.get_symbol_info(symbol_name)
                TradingSymbol.objects.update_or_create(
                    symbol=info.symbol,
                    defaults={
                        "broker_symbol": info.symbol,
                        "min_lot": info.min_lot,
                        "max_lot": info.max_lot,
                        "lot_step": info.lot_step,
                        "point": info.point,
                        "digits": info.digits,
                        "spread_limit_points": info.spread_points,
                    },
                )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        finally:
            broker.disconnect()
        self.stdout.write(self.style.SUCCESS("Symbol sync complete"))
