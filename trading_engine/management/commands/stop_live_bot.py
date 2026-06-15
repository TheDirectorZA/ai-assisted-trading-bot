from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from trading_engine.models import AuditLog, BotState


class Command(BaseCommand):
    help = "Stop bot loops."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")

    def handle(self, *args, **options):
        user = get_user_model().objects.get(username=options["username"])
        state, _ = BotState.objects.get_or_create(user=user)
        state.is_running = False
        state.save(update_fields=["is_running", "updated_at"])
        AuditLog.objects.create(
            user=user,
            action="LIVE_BOT_STOPPED",
            severity="INFO",
            description="Bot stopped from management command.",
        )
        self.stdout.write(self.style.SUCCESS("Bot stopped."))
