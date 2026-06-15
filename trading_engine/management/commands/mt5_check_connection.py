from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from trading_engine.brokers import MT5LiveBroker


class Command(BaseCommand):
    help = "Check MT5 connectivity and account retrieval without placing trades."

    def handle(self, *args, **options):
        broker = MT5LiveBroker()
        try:
            broker.connect()
            account = broker.get_account_info()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        finally:
            broker.disconnect()
        self.stdout.write(
            self.style.SUCCESS(
                f"Connected to MT5 account {account.account_number} on {account.server}; "
                f"trade_allowed={account.trade_allowed}"
            )
        )
