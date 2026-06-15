from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from trading_engine.brokers import MT5LiveBroker
from trading_engine.execution import LiveTradingEngine
from trading_engine.models import BotState


class Command(BaseCommand):
    help = "Run one live-engine cycle using the configured active symbol and strategy."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")

    def handle(self, *args, **options):
        user = get_user_model().objects.get(username=options["username"])
        state = BotState.objects.get(user=user)
        if state.active_symbol is None or state.active_strategy is None:
            raise CommandError("active symbol and strategy must be configured")
        broker = MT5LiveBroker()
        try:
            result = LiveTradingEngine(user=user, broker=broker).run_once(
                symbol=state.active_symbol,
                strategy_model=state.active_strategy,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        finally:
            broker.disconnect()
        self.stdout.write(f"{result.status}: {result.message}")
