from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from trading_engine.configuration import CONFIRMATION_PHRASE, LiveTradingSettings
from trading_engine.models import AuditLog, BotState, Strategy, TradingSymbol


class Command(BaseCommand):
    help = "Mark the live bot as running after confirmation and safety gate validation."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--symbol", required=True)
        parser.add_argument("--strategy", required=True)
        parser.add_argument("--confirm", required=True)

    def handle(self, *args, **options):
        if options["confirm"] != CONFIRMATION_PHRASE:
            raise CommandError("incorrect confirmation phrase")
        settings = LiveTradingSettings.from_env()
        settings.assert_live_trading_allowed()
        user = get_user_model().objects.get(username=options["username"])
        symbol = TradingSymbol.objects.get(symbol=options["symbol"])
        strategy = Strategy.objects.get(slug=options["strategy"])
        state, _ = BotState.objects.get_or_create(user=user)
        state.mode = "LIVE"
        state.is_running = True
        state.live_trading_armed = True
        state.active_symbol = symbol
        state.active_strategy = strategy
        state.save()
        AuditLog.objects.create(
            user=user,
            action="LIVE_BOT_STARTED",
            severity="CRITICAL",
            description="Live bot marked as running.",
        )
        self.stdout.write(self.style.SUCCESS("Live bot marked as running."))
