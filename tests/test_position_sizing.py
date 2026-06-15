from __future__ import annotations

from decimal import Decimal

from trading_engine.risk import calculate_risk_based_volume


def test_risk_based_position_sizing_rounds_to_lot_step() -> None:
    volume = calculate_risk_based_volume(
        account_equity=Decimal("10000"),
        risk_percentage=Decimal("1"),
        entry_price=Decimal("1.1000"),
        stop_loss_price=Decimal("1.0900"),
        point=Decimal("0.0001"),
        point_value_per_lot=Decimal("10"),
        lot_step=Decimal("0.01"),
        min_lot=Decimal("0.01"),
        max_lot=Decimal("10"),
        broker_max_lot=Decimal("100"),
    )

    assert volume == Decimal("0.10")
