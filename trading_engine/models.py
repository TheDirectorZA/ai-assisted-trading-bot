from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TradingMode(models.TextChoices):
    BACKTEST = "BACKTEST", "Backtest"
    PAPER = "PAPER", "Paper"
    LIVE = "LIVE", "Live"


class SignalType(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"
    HOLD = "HOLD", "Hold"


class OrderStatus(models.TextChoices):
    NEW = "NEW", "New"
    PRE_CHECKED = "PRE_CHECKED", "Pre-checked"
    SENT = "SENT", "Sent"
    FILLED = "FILLED", "Filled"
    PARTIALLY_FILLED = "PARTIALLY_FILLED", "Partially filled"
    REJECTED = "REJECTED", "Rejected"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    CLOSED = "CLOSED", "Closed"


class Side(models.TextChoices):
    BUY = "BUY", "Buy"
    SELL = "SELL", "Sell"


class TradingSymbol(TimestampedModel):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128, blank=True)
    market_type = models.CharField(max_length=32, default="forex")
    broker_symbol = models.CharField(max_length=64)
    timeframe = models.CharField(max_length=16, default="M5")
    min_lot = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0.01"))
    max_lot = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("100"))
    lot_step = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0.01"))
    point = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal("0.0001"))
    digits = models.PositiveSmallIntegerField(default=5)
    spread_limit_points = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("30")
    )
    is_active = models.BooleanField(default=True)
    is_live_enabled = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["symbol"]),
            models.Index(fields=["is_active", "is_live_enabled"]),
        ]

    def __str__(self) -> str:
        return self.symbol


class Candle(models.Model):
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.CASCADE, related_name="candles")
    timestamp = models.DateTimeField()
    open = models.DecimalField(max_digits=20, decimal_places=8)
    high = models.DecimalField(max_digits=20, decimal_places=8)
    low = models.DecimalField(max_digits=20, decimal_places=8)
    close = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    timeframe = models.CharField(max_length=16, default="M5")
    source = models.CharField(max_length=32, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["symbol", "timestamp", "timeframe", "source"],
                name="uniq_candle_symbol_timeframe_source",
            )
        ]
        indexes = [
            models.Index(fields=["symbol", "timeframe", "timestamp"]),
            models.Index(fields=["source", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.symbol} {self.timeframe} {self.timestamp.isoformat()}"


class LiveTick(models.Model):
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.CASCADE, related_name="ticks")
    broker_time = models.DateTimeField()
    local_time = models.DateTimeField()
    bid = models.DecimalField(max_digits=20, decimal_places=8)
    ask = models.DecimalField(max_digits=20, decimal_places=8)
    last = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    volume = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal("0"))
    spread_points = models.DecimalField(max_digits=18, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["symbol", "-broker_time"]),
            models.Index(fields=["created_at"]),
        ]


class LiveCandleSyncLog(models.Model):
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.CASCADE)
    timeframe = models.CharField(max_length=16)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    candles_created = models.PositiveIntegerField(default=0)
    candles_updated = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default="STARTED")
    message = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["symbol", "timeframe", "-started_at"])]


class MarketDataHealthCheck(models.Model):
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.CASCADE)
    checked_at = models.DateTimeField(auto_now_add=True)
    latest_tick_at = models.DateTimeField(null=True, blank=True)
    latest_candle_at = models.DateTimeField(null=True, blank=True)
    tick_age_seconds = models.PositiveIntegerField(null=True, blank=True)
    candle_age_seconds = models.PositiveIntegerField(null=True, blank=True)
    is_fresh = models.BooleanField(default=False)
    spread_points = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["symbol", "-checked_at", "is_fresh"])]


class Strategy(TimestampedModel):
    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    strategy_type = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    is_live_enabled = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "is_live_enabled"]),
        ]

    def __str__(self) -> str:
        return self.name


class StrategyParameter(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=64)
    value = models.CharField(max_length=255)
    value_type = models.CharField(max_length=32, default="str")
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["strategy", "name"], name="uniq_strategy_parameter")
        ]
        indexes = [models.Index(fields=["strategy", "name"])]

    def __str__(self) -> str:
        return f"{self.strategy.slug}.{self.name}"


class Signal(models.Model):
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    timeframe = models.CharField(max_length=16, default="M5")
    signal_type = models.CharField(max_length=8, choices=SignalType.choices)
    price = models.DecimalField(max_digits=20, decimal_places=8)
    confidence = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0"))
    reason = models.TextField(blank=True)
    mode = models.CharField(max_length=16, choices=TradingMode.choices, default=TradingMode.PAPER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["strategy", "symbol", "timeframe", "timestamp", "signal_type", "mode"],
                name="uniq_signal_deduplication_key",
            )
        ]
        indexes = [
            models.Index(fields=["symbol", "strategy", "-timestamp"]),
            models.Index(fields=["mode", "-created_at"]),
        ]


class RiskSettings(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    max_risk_per_trade_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("1.0")
    )
    max_daily_loss_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("3.0")
    )
    max_weekly_loss_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("7.0")
    )
    max_open_positions = models.PositiveIntegerField(default=3)
    max_positions_per_symbol = models.PositiveIntegerField(default=1)
    max_leverage = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("30"))
    max_lot_size = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1.0"))
    min_stop_loss_points = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("50")
    )
    max_stop_loss_points = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("2000")
    )
    max_spread_points = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("30"))
    max_slippage_points = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("20")
    )
    stop_trading_after_losses = models.PositiveIntegerField(default=3)
    stale_data_threshold_seconds = models.PositiveIntegerField(default=10)
    max_price_jump_percentage = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("1.0")
    )
    require_stop_loss = models.BooleanField(default=True)
    require_take_profit = models.BooleanField(default=False)
    trading_start_time = models.TimeField(null=True, blank=True)
    trading_end_time = models.TimeField(null=True, blank=True)
    allowed_symbols = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user"])]


class BrokerAccount(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_name = models.CharField(max_length=64, default="MT5")
    account_number = models.CharField(max_length=64, blank=True)
    server = models.CharField(max_length=128, blank=True)
    currency = models.CharField(max_length=16, blank=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    margin = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    free_margin = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    leverage = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    trade_allowed = models.BooleanField(default=False)
    connected = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "broker_name", "account_number"])]


class LiveOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_account = models.ForeignKey(
        BrokerAccount, on_delete=models.CASCADE, null=True, blank=True
    )
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    signal = models.ForeignKey(Signal, on_delete=models.SET_NULL, null=True, blank=True)
    broker_order_id = models.CharField(max_length=128, blank=True)
    broker_deal_id = models.CharField(max_length=128, blank=True)
    side = models.CharField(max_length=8, choices=Side.choices)
    order_type = models.CharField(max_length=32, default="MARKET")
    requested_volume = models.DecimalField(max_digits=18, decimal_places=6)
    filled_volume = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    requested_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    filled_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    deviation_points = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.NEW)
    broker_retcode = models.CharField(max_length=64, blank=True)
    broker_comment = models.TextField(blank=True)
    raw_request_json = models.JSONField(default=dict, blank=True)
    raw_response_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "-created_at"]),
            models.Index(fields=["symbol", "side", "-created_at"]),
            models.Index(fields=["broker_order_id"]),
        ]


class LivePosition(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_account = models.ForeignKey(
        BrokerAccount, on_delete=models.CASCADE, null=True, blank=True
    )
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    broker_position_id = models.CharField(max_length=128, unique=True)
    side = models.CharField(max_length=8, choices=Side.choices)
    volume = models.DecimalField(max_digits=18, decimal_places=6)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    swap = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    commission = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=32, default="OPEN")
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "symbol"]),
            models.Index(fields=["broker_position_id"]),
        ]


class TradeJournalEntry(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.SET_NULL, null=True, blank=True)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=16, choices=TradingMode.choices, default=TradingMode.PAPER)
    related_order = models.ForeignKey(LiveOrder, on_delete=models.SET_NULL, null=True, blank=True)
    related_position = models.ForeignKey(
        LivePosition, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    emotions = models.TextField(blank=True)
    mistakes = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "mode", "-created_at"])]


class BacktestRun(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    initial_balance = models.DecimalField(max_digits=20, decimal_places=2)
    final_balance = models.DecimalField(max_digits=20, decimal_places=2)
    total_return = models.DecimalField(max_digits=12, decimal_places=4)
    max_drawdown = models.DecimalField(max_digits=12, decimal_places=4)
    win_rate = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0"))
    profit_factor = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0"))
    total_trades = models.PositiveIntegerField(default=0)
    parameters = models.JSONField(default=dict, blank=True)
    metrics_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["symbol", "strategy", "-created_at"])]


class BacktestTrade(models.Model):
    backtest_run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name="trades")
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    exit_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    side = models.CharField(max_length=8, choices=Side.choices)
    pnl = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    pnl_percentage = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0"))
    exit_reason = models.CharField(max_length=128, blank=True)

    class Meta:
        indexes = [models.Index(fields=["backtest_run", "symbol"])]


class PaperAccount(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default="Demo paper account")
    starting_balance = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("10000")
    )
    current_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("10000"))
    equity = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("10000"))
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["user", "is_active"])]


class PaperOrder(models.Model):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name="orders")
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    side = models.CharField(max_length=8, choices=Side.choices)
    order_type = models.CharField(max_length=32, default="MARKET")
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    requested_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    filled_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.NEW)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["account", "status", "-created_at"])]


class PaperPosition(models.Model):
    account = models.ForeignKey(PaperAccount, on_delete=models.CASCADE, related_name="positions")
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.PROTECT)
    side = models.CharField(max_length=8, choices=Side.choices)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    entry_price = models.DecimalField(max_digits=20, decimal_places=8)
    current_price = models.DecimalField(max_digits=20, decimal_places=8)
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="OPEN")

    class Meta:
        indexes = [models.Index(fields=["account", "status", "symbol"])]


class BotState(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mode = models.CharField(max_length=16, choices=TradingMode.choices, default=TradingMode.PAPER)
    is_running = models.BooleanField(default=False)
    live_trading_armed = models.BooleanField(default=False)
    kill_switch_active = models.BooleanField(default=False)
    active_strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    active_symbol = models.ForeignKey(
        TradingSymbol, on_delete=models.SET_NULL, null=True, blank=True
    )
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "mode", "is_running", "kill_switch_active"])]


class AIReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "report_type", "-created_at"])]


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=128)
    severity = models.CharField(max_length=32, default="INFO")
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["action", "severity", "-created_at"])]


class RiskEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    symbol = models.ForeignKey(TradingSymbol, on_delete=models.SET_NULL, null=True, blank=True)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=64)
    severity = models.CharField(max_length=32, default="WARNING")
    decision = models.CharField(max_length=32, default="BLOCKED")
    triggered_rules = models.JSONField(default=list, blank=True)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["event_type", "decision", "-created_at"])]
