from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from trading_engine.models import AuditLog, BotState


class Command(BaseCommand):
    help = "Immediately activate the kill switch and stop bot loops."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")

    def handle(self, *args, **options):
        user = get_user_model().objects.get(username=options["username"])
        state, _ = BotState.objects.get_or_create(user=user)
        state.kill_switch_active = True
        state.is_running = False
        state.save(update_fields=["kill_switch_active", "is_running", "updated_at"])
        AuditLog.objects.create(
            user=user,
            action="KILL_SWITCH_ACTIVATED",
            severity="CRITICAL",
            description="Kill switch activated from management command.",
        )
        self.stdout.write(self.style.WARNING("Kill switch activated. New orders are blocked."))
