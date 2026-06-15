from __future__ import annotations

from django.core.management.base import BaseCommand

from trading_engine.backtesting import run_backtest
from trading_engine.models import Strategy, TradingSymbol


class Command(BaseCommand):
    help = "Run a deterministic demo backtest."

    def handle(self, *args, **options):
        symbol = TradingSymbol.objects.get(symbol="EURUSD")
        strategy = Strategy.objects.get(slug="moving-average-crossover")
        backtest = run_backtest(symbol=symbol, strategy_model=strategy)
        message = (
            f"Backtest {backtest.id}: final={backtest.final_balance} "
            f"return={backtest.total_return}%"
        )
        self.stdout.write(self.style.SUCCESS(message))
