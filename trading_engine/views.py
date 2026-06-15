from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from trading_engine.configuration import CONFIRMATION_PHRASE, LiveTradingSettings
from trading_engine.models import (
    AIReport,
    AuditLog,
    BacktestRun,
    BotState,
    BrokerAccount,
    LiveOrder,
    LivePosition,
    RiskEvent,
    RiskSettings,
    Signal,
    Strategy,
    TradingSymbol,
)


@login_required
def dashboard(request):
    state = _get_state(request.user)
    account = BrokerAccount.objects.filter(user=request.user).order_by("-last_sync_at").first()
    daily_pnl = (
        LivePosition.objects.filter(user=request.user, opened_at__date=timezone.localdate())
        .aggregate(total=Sum("unrealized_pnl"))
        .get("total")
        or 0
    )
    return render(
        request,
        "trading_engine/dashboard.html",
        {
            "settings": LiveTradingSettings.from_env(),
            "state": state,
            "account": account,
            "open_positions": LivePosition.objects.filter(user=request.user, status="OPEN")[:20],
            "daily_pnl": daily_pnl,
            "latest_signals": Signal.objects.order_by("-created_at")[:10],
            "latest_orders": LiveOrder.objects.filter(user=request.user).order_by("-created_at")[
                :10
            ],
            "risk_events": RiskEvent.objects.filter(user=request.user).order_by("-created_at")[:10],
        },
    )


@login_required
def broker_connection(request):
    return render(
        request,
        "trading_engine/broker_connection.html",
        {
            "account": BrokerAccount.objects.filter(user=request.user)
            .order_by("-last_sync_at")
            .first(),
            "env_names": ["MT5_LOGIN", "MT5_SERVER", "MT5_TERMINAL_PATH"],
        },
    )


@login_required
def live_controls(request):
    state = _get_state(request.user)
    live_settings = LiveTradingSettings.from_env()
    return render(
        request,
        "trading_engine/live_controls.html",
        {
            "state": state,
            "live_settings": live_settings,
            "activation_errors": live_settings.activation_errors(),
            "confirmation_phrase": CONFIRMATION_PHRASE,
        },
    )


@login_required
def symbols(request):
    return render(
        request,
        "trading_engine/list.html",
        {"title": "Symbols", "items": TradingSymbol.objects.all()},
    )


@login_required
def strategies(request):
    return render(
        request,
        "trading_engine/list.html",
        {"title": "Strategies", "items": Strategy.objects.all()},
    )


@login_required
def backtests(request):
    return render(
        request,
        "trading_engine/list.html",
        {"title": "Backtests", "items": BacktestRun.objects.order_by("-created_at")[:50]},
    )


@login_required
def paper_trading(request):
    return render(request, "trading_engine/static_page.html", {"title": "Paper Trading"})


@login_required
def live_orders(request):
    return render(
        request,
        "trading_engine/list.html",
        {
            "title": "Live Orders",
            "items": LiveOrder.objects.filter(user=request.user).order_by("-created_at"),
        },
    )


@login_required
def live_positions(request):
    return render(
        request,
        "trading_engine/list.html",
        {
            "title": "Live Positions",
            "items": LivePosition.objects.filter(user=request.user).order_by("-opened_at"),
        },
    )


@login_required
def risk_settings(request):
    settings_obj, _ = RiskSettings.objects.get_or_create(user=request.user)
    return render(request, "trading_engine/risk_settings.html", {"risk_settings": settings_obj})


@login_required
def risk_events(request):
    return render(
        request,
        "trading_engine/list.html",
        {
            "title": "Risk Events",
            "items": RiskEvent.objects.filter(user=request.user).order_by("-created_at"),
        },
    )


@login_required
def trade_journal(request):
    return render(request, "trading_engine/static_page.html", {"title": "Trade Journal"})


@login_required
def ai_reports(request):
    return render(
        request,
        "trading_engine/list.html",
        {
            "title": "AI Reports",
            "items": AIReport.objects.filter(user=request.user).order_by("-created_at"),
        },
    )


@login_required
def audit_logs(request):
    return render(
        request,
        "trading_engine/list.html",
        {"title": "Audit Logs", "items": AuditLog.objects.order_by("-created_at")},
    )


@login_required
@require_POST
def activate_kill_switch(request):
    state = _get_state(request.user)
    state.kill_switch_active = True
    state.is_running = False
    state.save(update_fields=["kill_switch_active", "is_running", "updated_at"])
    AuditLog.objects.create(
        user=request.user,
        action="KILL_SWITCH_ACTIVATED",
        severity="CRITICAL",
        description="Dashboard kill switch activated.",
    )
    return redirect("trading_engine:live_controls")


def _get_state(user) -> BotState:
    state, _ = BotState.objects.get_or_create(user=user)
    return state
