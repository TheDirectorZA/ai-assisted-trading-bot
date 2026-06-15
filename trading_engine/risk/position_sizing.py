from __future__ import annotations

from decimal import ROUND_DOWN, Decimal


class PositionSizingError(ValueError):
    """Raised when a safe risk-based position size cannot be calculated."""


def calculate_risk_based_volume(
    *,
    account_equity: Decimal,
    risk_percentage: Decimal,
    entry_price: Decimal,
    stop_loss_price: Decimal,
    point: Decimal,
    point_value_per_lot: Decimal,
    lot_step: Decimal,
    min_lot: Decimal,
    max_lot: Decimal,
    broker_max_lot: Decimal,
) -> Decimal:
    if account_equity <= 0:
        raise PositionSizingError("account equity must be greater than zero")
    if risk_percentage <= 0:
        raise PositionSizingError("risk percentage must be greater than zero")
    if point <= 0 or point_value_per_lot <= 0:
        raise PositionSizingError("point and point value must be greater than zero")
    if lot_step <= 0 or min_lot <= 0 or max_lot <= 0 or broker_max_lot <= 0:
        raise PositionSizingError("lot limits and lot step must be greater than zero")

    stop_distance_points = abs(entry_price - stop_loss_price) / point
    if stop_distance_points <= 0:
        raise PositionSizingError("stop loss must be away from entry price")

    max_loss = account_equity * (risk_percentage / Decimal("100"))
    raw_volume = max_loss / (stop_distance_points * point_value_per_lot)
    capped = min(raw_volume, max_lot, broker_max_lot)
    stepped = _round_down_to_step(capped, lot_step)
    if stepped < min_lot:
        raise PositionSizingError("calculated volume is below broker minimum lot")
    return stepped


def _round_down_to_step(value: Decimal, step: Decimal) -> Decimal:
    steps = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return (steps * step).quantize(step)
