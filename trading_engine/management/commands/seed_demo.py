from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from trading_engine.models import Candle, RiskSettings, Strategy, StrategyParameter, TradingSymbol


class Command(BaseCommand):
    help = "Seed local demo symbols, strategies, risk settings, and candles."

    def handle(self, *args, **options):
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(username="demo", defaults={"is_staff": True})
        RiskSettings.objects.get_or_create(user=user)
        symbol, _ = TradingSymbol.objects.update_or_create(
            symbol="EURUSD",
            defaults={
                "name": "Euro / US Dollar",
                "market_type": "forex",
                "broker_symbol": "EURUSD",
                "timeframe": "M5",
                "min_lot": Decimal("0.01"),
                "max_lot": Decimal("100"),
                "lot_step": Decimal("0.01"),
                "point": Decimal("0.0001"),
                "digits": 5,
                "spread_limit_points": Decimal("30"),
                "is_active": True,
                "is_live_enabled": False,
            },
        )
        strategy, _ = Strategy.objects.update_or_create(
            slug="moving-average-crossover",
            defaults={
                "name": "Moving Average Crossover",
                "description": "Deterministic moving-average crossover strategy.",
                "strategy_type": "technical",
                "is_active": True,
                "is_live_enabled": False,
            },
        )
        defaults = {"short_window": ("3", "int"), "long_window": ("5", "int")}
        for name, (value, value_type) in defaults.items():
            StrategyParameter.objects.update_or_create(
                strategy=strategy,
                name=name,
                defaults={"value": value, "value_type": value_type},
            )
        start = timezone.now() - timezone.timedelta(minutes=5 * 40)
        price = Decimal("1.1000")
        created = 0
        for index in range(40):
            timestamp = (start + timezone.timedelta(minutes=5 * index)).replace(
                second=0, microsecond=0
            )
            if index % 7 == 0:
                price -= Decimal("0.0004")
            else:
                price += Decimal("0.0002")
            _, was_created = Candle.objects.update_or_create(
                symbol=symbol,
                timestamp=timestamp,
                timeframe="M5",
                source="DEMO",
                defaults={
                    "open": price - Decimal("0.0001"),
                    "high": price + Decimal("0.0003"),
                    "low": price - Decimal("0.0003"),
                    "close": price,
                    "volume": Decimal("1000"),
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded demo data. New candles: {created}"))
