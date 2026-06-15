from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from trading_engine.brokers import MT5LiveBroker
from trading_engine.execution import LiveTradingEngine


class Command(BaseCommand):
    help = "Sync MT5 account information into the database."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")

    def handle(self, *args, **options):
        user = get_user_model().objects.get(username=options["username"])
        broker = MT5LiveBroker()
        try:
            broker.connect()
            account = LiveTradingEngine(user=user, broker=broker).sync_account()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        finally:
            broker.disconnect()
        self.stdout.write(self.style.SUCCESS(f"Synced account {account.account_number}"))
