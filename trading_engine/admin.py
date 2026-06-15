from __future__ import annotations

from django.contrib import admin

from trading_engine import models


@admin.register(models.TradingSymbol)
class TradingSymbolAdmin(admin.ModelAdmin):
    list_display = ("symbol", "broker_symbol", "timeframe", "is_active", "is_live_enabled")
    list_filter = ("market_type", "is_active", "is_live_enabled")
    search_fields = ("symbol", "broker_symbol", "name")


@admin.register(models.Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ("symbol", "timeframe", "timestamp", "close", "source")
    list_filter = ("timeframe", "source")
    search_fields = ("symbol__symbol",)


@admin.register(models.LiveTick)
class LiveTickAdmin(admin.ModelAdmin):
    list_display = ("symbol", "broker_time", "bid", "ask", "spread_points")
    list_filter = ("symbol",)


@admin.register(models.LiveCandleSyncLog)
class LiveCandleSyncLogAdmin(admin.ModelAdmin):
    list_display = ("symbol", "timeframe", "status", "candles_created", "started_at")


@admin.register(models.MarketDataHealthCheck)
class MarketDataHealthCheckAdmin(admin.ModelAdmin):
    list_display = ("symbol", "checked_at", "is_fresh", "tick_age_seconds", "candle_age_seconds")


class StrategyParameterInline(admin.TabularInline):
    model = models.StrategyParameter
    extra = 0


@admin.register(models.Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "strategy_type", "is_active", "is_live_enabled")
    list_filter = ("strategy_type", "is_active", "is_live_enabled")
    search_fields = ("name", "slug")
    inlines = [StrategyParameterInline]


@admin.register(models.Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ("symbol", "strategy", "timeframe", "timestamp", "signal_type", "mode")
    list_filter = ("signal_type", "mode", "timeframe")
    search_fields = ("symbol__symbol", "strategy__slug")


@admin.register(models.RiskSettings)
class RiskSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "max_risk_per_trade_percentage",
        "max_daily_loss_percentage",
        "max_open_positions",
        "require_stop_loss",
        "require_take_profit",
    )


@admin.register(models.BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "broker_name", "account_number", "server", "connected", "trade_allowed")
    list_filter = ("broker_name", "connected", "trade_allowed")
    search_fields = ("account_number", "server", "user__username")


@admin.register(models.LiveOrder)
class LiveOrderAdmin(admin.ModelAdmin):
    list_display = ("user", "symbol", "side", "requested_volume", "status", "broker_retcode")
    list_filter = ("status", "side", "order_type")
    search_fields = ("broker_order_id", "broker_deal_id", "symbol__symbol")


@admin.register(models.LivePosition)
class LivePositionAdmin(admin.ModelAdmin):
    list_display = ("user", "symbol", "side", "volume", "status", "unrealized_pnl")
    list_filter = ("status", "side")
    search_fields = ("broker_position_id", "symbol__symbol")


@admin.register(models.TradeJournalEntry)
class TradeJournalEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "mode", "created_at")
    list_filter = ("mode",)
    search_fields = ("title", "notes", "lessons")


@admin.register(models.BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ("strategy", "symbol", "initial_balance", "final_balance", "total_return")
    list_filter = ("strategy", "symbol")


@admin.register(models.BacktestTrade)
class BacktestTradeAdmin(admin.ModelAdmin):
    list_display = ("backtest_run", "symbol", "side", "quantity", "pnl")


@admin.register(models.PaperAccount)
class PaperAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "current_balance", "equity", "is_active")


@admin.register(models.PaperOrder)
class PaperOrderAdmin(admin.ModelAdmin):
    list_display = ("account", "symbol", "side", "quantity", "status")
    list_filter = ("status", "side")


@admin.register(models.PaperPosition)
class PaperPositionAdmin(admin.ModelAdmin):
    list_display = ("account", "symbol", "side", "quantity", "status", "unrealized_pnl")
    list_filter = ("status", "side")


@admin.register(models.BotState)
class BotStateAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "is_running", "live_trading_armed", "kill_switch_active")
    list_filter = ("mode", "is_running", "kill_switch_active")


@admin.register(models.AIReport)
class AIReportAdmin(admin.ModelAdmin):
    list_display = ("user", "report_type", "title", "created_at")
    list_filter = ("report_type",)
    search_fields = ("title", "content")


@admin.register(models.AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "severity", "user", "created_at")
    list_filter = ("severity", "action")
    search_fields = ("description",)


@admin.register(models.RiskEvent)
class RiskEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "decision", "severity", "symbol", "strategy", "created_at")
    list_filter = ("event_type", "decision", "severity")
