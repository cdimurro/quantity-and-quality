from __future__ import annotations

import math
from typing import Optional

from .core import Number, _require_nonnegative, _require_positive, weighted_exergy_factor


def exergy_capital_efficiency(delta_exergy: Number, capital_cost: Number) -> float:
    """Return Exergy Capital Efficiency, `delta X_A / capital cost`."""

    exergy = float(delta_exergy)
    cost = float(capital_cost)
    _require_nonnegative(exergy, "delta_exergy")
    _require_positive(cost, "capital_cost")
    return exergy / cost


def exergy_capital_efficiency_rate(delta_exergy_rate: Number, capital_cost: Number) -> float:
    """Return rate-based Exergy Capital Efficiency, `delta Xdot_A / capital cost`."""

    rate = float(delta_exergy_rate)
    cost = float(capital_cost)
    _require_nonnegative(rate, "delta_exergy_rate")
    _require_positive(cost, "capital_cost")
    return rate / cost


def second_law_efficiency(input_exergy: Number, useful_output_exergy: Number) -> float:
    """Return second-law efficiency for a declared process boundary."""

    input_value = float(input_exergy)
    output_value = float(useful_output_exergy)
    _require_positive(input_value, "input_exergy")
    _require_nonnegative(output_value, "useful_output_exergy")
    if output_value > input_value:
        raise ValueError("useful_output_exergy cannot exceed input_exergy")
    return output_value / input_value


def exergy_loss_angle(
    input_exergy: Number,
    useful_output_exergy: Number,
    *,
    degrees: bool = True,
) -> Optional[float]:
    """Return the Exergy Loss Angle for a declared process boundary.

    The angle is a diagnostic coordinate derived from second-law efficiency.
    If both useful output and non-retained exergy are zero, the angle is
    physically undefined and `None` is returned.
    """

    input_value = float(input_exergy)
    output_value = float(useful_output_exergy)
    _require_nonnegative(input_value, "input_exergy")
    _require_nonnegative(output_value, "useful_output_exergy")
    if output_value > input_value:
        raise ValueError("useful_output_exergy cannot exceed input_exergy")
    lost = input_value - output_value
    if lost == 0 and output_value == 0:
        return None
    angle = math.atan2(lost, output_value)
    return math.degrees(angle) if degrees else angle


def exergy_loss_angle_from_efficiency(eta_x: Number, *, degrees: bool = True) -> float:
    """Return Exergy Loss Angle from second-law efficiency."""

    eta = float(eta_x)
    if not math.isfinite(eta) or eta < 0 or eta > 1:
        raise ValueError("eta_x must be between 0 and 1")
    if eta == 0:
        angle = math.pi / 2.0
    else:
        angle = math.atan((1.0 - eta) / eta)
    return math.degrees(angle) if degrees else angle


def efficiency_from_loss_angle(theta_loss: Number, *, degrees: bool = True) -> float:
    """Return second-law efficiency from Exergy Loss Angle."""

    angle = math.radians(float(theta_loss)) if degrees else float(theta_loss)
    if not math.isfinite(angle) or angle < 0 or angle > math.pi / 2.0:
        raise ValueError("theta_loss must be between 0 and 90 degrees")
    return 1.0 / (1.0 + math.tan(angle))


def loss_angle_velocity(
    previous_theta: Number,
    current_theta: Number,
    delta_time: Number,
) -> float:
    """Return Loss Angle Velocity over a declared time interval."""

    previous = float(previous_theta)
    current = float(current_theta)
    dt = float(delta_time)
    _require_positive(dt, "delta_time")
    if not math.isfinite(previous) or not math.isfinite(current):
        raise ValueError("angles must be finite")
    return (current - previous) / dt


def weighted_f3_exergy_factor(records) -> float:
    """Alias for the F3 energy-weighted interval Exergy Factor equation."""

    return weighted_exergy_factor(records)
