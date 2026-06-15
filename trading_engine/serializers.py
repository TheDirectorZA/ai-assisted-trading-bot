from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from trading_engine import models


class TradingSymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TradingSymbol
        fields = "__all__"


class CandleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Candle
        fields = "__all__"


class LiveTickSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LiveTick
        fields = "__all__"


class StrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Strategy
        fields = "__all__"


class StrategyParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StrategyParameter
        fields = "__all__"


class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Signal
        fields = "__all__"


class RiskSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RiskSettings
        fields = "__all__"

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        max_risk = attrs.get("max_risk_per_trade_percentage")
        max_daily_loss = attrs.get("max_daily_loss_percentage")
        if isinstance(max_risk, Decimal) and max_risk <= 0:
            raise serializers.ValidationError("Risk per trade must be greater than zero.")
        if isinstance(max_daily_loss, Decimal) and max_daily_loss <= 0:
            raise serializers.ValidationError("Daily loss limit must be greater than zero.")
        return attrs


class BrokerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BrokerAccount
        fields = "__all__"


class LiveOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LiveOrder
        fields = "__all__"


class LivePositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LivePosition
        fields = "__all__"


class TradeJournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TradeJournalEntry
        fields = "__all__"


class BacktestRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BacktestRun
        fields = "__all__"


class PaperAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaperAccount
        fields = "__all__"


class BotStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.BotState
        fields = "__all__"


class AIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AIReport
        fields = "__all__"


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AuditLog
        fields = "__all__"


class RiskEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RiskEvent
        fields = "__all__"
