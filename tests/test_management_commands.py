from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_mt5_test_order_refuses_without_exact_confirmation() -> None:
    with pytest.raises(CommandError, match="incorrect confirmation phrase"):
        call_command(
            "mt5_test_order",
            symbol="XAUUSD",
            volume="0.01",
            stop_loss="1900",
            confirm="WRONG",
        )
