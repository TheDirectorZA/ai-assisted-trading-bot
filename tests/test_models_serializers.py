from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from trading_engine.models import RiskSettings, Strategy, TradingSymbol
from trading_engine.serializers import TradingSymbolSerializer


@pytest.mark.django_db
def test_core_models_can_be_created() -> None:
    user = get_user_model().objects.create_user(username="alice")
    symbol = TradingSymbol.objects.create(symbol="EURUSD", broker_symbol="EURUSD")
    strategy = Strategy.objects.create(
        name="Moving Average Crossover",
        slug="moving-average-crossover",
        strategy_type="technical",
    )
    risk = RiskSettings.objects.create(user=user, max_risk_per_trade_percentage=Decimal("0.5"))

    assert str(symbol) == "EURUSD"
    assert str(strategy) == "Moving Average Crossover"
    assert risk.require_stop_loss is True


@pytest.mark.django_db
def test_trading_symbol_serializer_validates() -> None:
    serializer = TradingSymbolSerializer(
        data={
            "symbol": "XAUUSD",
            "broker_symbol": "XAUUSD",
            "timeframe": "M5",
            "min_lot": "0.01",
            "max_lot": "100",
            "lot_step": "0.01",
            "point": "0.01",
            "digits": 2,
            "spread_limit_points": "50",
            "is_active": True,
            "is_live_enabled": False,
        }
    )

    assert serializer.is_valid(), serializer.errors
