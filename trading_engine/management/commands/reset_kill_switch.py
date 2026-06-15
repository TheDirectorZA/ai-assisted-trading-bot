from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from trading_engine.configuration import CONFIRMATION_PHRASE
from trading_engine.models import AuditLog, BotState


class Command(BaseCommand):
    help = "Reset the kill switch after manual review."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--confirm", required=True)

    def handle(self, *args, **options):
        if options["confirm"] != CONFIRMATION_PHRASE:
            raise CommandError("incorrect confirmation phrase")
        user = get_user_model().objects.get(username=options["username"])
        state, _ = BotState.objects.get_or_create(user=user)
        state.kill_switch_active = False
        state.save(update_fields=["kill_switch_active", "updated_at"])
        AuditLog.objects.create(
            user=user,
            action="KILL_SWITCH_RESET",
            severity="WARNING",
            description="Kill switch reset from management command.",
        )
        self.stdout.write(self.style.SUCCESS("Kill switch reset."))
