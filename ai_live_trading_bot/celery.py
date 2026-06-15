from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_live_trading_bot.settings")

app = Celery("ai_live_trading_bot")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
