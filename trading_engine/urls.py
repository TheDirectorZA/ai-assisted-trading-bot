from __future__ import annotations

from django.urls import path

from trading_engine import views

app_name = "trading_engine"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("broker/", views.broker_connection, name="broker_connection"),
    path("live/", views.live_controls, name="live_controls"),
    path("live/kill-switch/", views.activate_kill_switch, name="activate_kill_switch"),
    path("symbols/", views.symbols, name="symbols"),
    path("strategies/", views.strategies, name="strategies"),
    path("backtests/", views.backtests, name="backtests"),
    path("paper/", views.paper_trading, name="paper_trading"),
    path("orders/", views.live_orders, name="live_orders"),
    path("positions/", views.live_positions, name="live_positions"),
    path("risk-settings/", views.risk_settings, name="risk_settings"),
    path("risk-events/", views.risk_events, name="risk_events"),
    path("journal/", views.trade_journal, name="trade_journal"),
    path("ai-reports/", views.ai_reports, name="ai_reports"),
    path("audit-logs/", views.audit_logs, name="audit_logs"),
]
