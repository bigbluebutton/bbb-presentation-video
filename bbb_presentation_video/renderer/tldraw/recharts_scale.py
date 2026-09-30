# SPDX-FileCopyrightText: 2015 Sen Yang
# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: MIT

"""Tick calculation for a numeric chart axis.

This is a Python port of ``getNiceTickValues`` and the functions it depends on
from recharts-scale 0.4.5 (``src/getNiceTickValues.js`` and
``src/util/arithmetic.js`` in https://github.com/recharts/recharts-scale).
recharts uses it to pick the ticks of a numeric axis with an automatic domain,
and then extends the axis domain to cover the ticks.
"""

import math
from decimal import Decimal
from typing import List, Tuple


def get_digit_count(value: float) -> int:
    if value == 0:
        return 1
    return math.floor(math.log10(abs(value))) + 1


def get_format_step(
    rough_step: Decimal, allow_decimals: bool, correction_factor: int
) -> Decimal:
    """Calculate the step which is easy to understand between ticks, like 10, 20, 25"""
    if rough_step <= 0:
        return Decimal(0)
    digit_count = get_digit_count(float(rough_step))
    # The ratio between the rough step and the smallest number which has a bigger
    # order of magnitudes than the rough step
    digit_count_value = Decimal(10) ** digit_count
    step_ratio = rough_step / digit_count_value
    step_ratio_scale = Decimal("0.05") if digit_count != 1 else Decimal("0.1")
    amend_step_ratio = (
        Decimal(math.ceil(step_ratio / step_ratio_scale)) + correction_factor
    ) * step_ratio_scale
    format_step = amend_step_ratio * digit_count_value
    return format_step if allow_decimals else Decimal(math.ceil(format_step))


def get_tick_of_single_value(
    value: float, tick_count: int, allow_decimals: bool
) -> List[Decimal]:
    """Calculate the ticks when the minimum value equals to the maximum value"""
    step = Decimal(1)
    # Calculate the middle value of ticks
    middle = Decimal(value)
    if middle != middle.to_integral_value() and allow_decimals:
        abs_value = abs(value)
        if abs_value < 1:
            # The step should be a float number when the difference is smaller than 1
            step = Decimal(10) ** (get_digit_count(value) - 1)
            middle = Decimal(math.floor(middle / step)) * step
        elif abs_value > 1:
            # Return the maximum integer which is smaller than 'value' when 'value' is
            # greater than 1
            middle = Decimal(math.floor(value))
    elif value == 0:
        middle = Decimal(math.floor((tick_count - 1) / 2))
    elif not allow_decimals:
        middle = Decimal(math.floor(value))
    middle_index = math.floor((tick_count - 1) / 2)
    return [middle + (n - middle_index) * step for n in range(tick_count)]


def calculate_step(
    minimum: float,
    maximum: float,
    tick_count: int,
    allow_decimals: bool,
    correction_factor: int = 0,
) -> Tuple[Decimal, Decimal, Decimal]:
    """Calculate the step, the minimum value of ticks and the maximum value of ticks"""
    # The step which is easy to understand between two ticks
    rough_step = (Decimal(maximum) - Decimal(minimum)) / (tick_count - 1)
    step = get_format_step(rough_step, allow_decimals, correction_factor)
    if minimum <= 0 <= maximum:
        # When 0 is inside the interval, 0 should be a tick
        middle = Decimal(0)
    else:
        middle = (Decimal(minimum) + Decimal(maximum)) / 2
        middle = middle - middle % step
    below_count = math.ceil((middle - Decimal(minimum)) / step)
    up_count = math.ceil((Decimal(maximum) - middle) / step)
    scale_count = below_count + up_count + 1
    if scale_count > tick_count:
        # When more ticks need to cover the interval, step should be bigger.
        return calculate_step(
            minimum, maximum, tick_count, allow_decimals, correction_factor + 1
        )
    if scale_count < tick_count:
        # When less ticks can cover the interval, we should add some additional ticks
        if maximum > 0:
            up_count += tick_count - scale_count
        else:
            below_count += tick_count - scale_count
    return step, middle - below_count * step, middle + up_count * step


def get_nice_tick_values(
    domain: Tuple[float, float], tick_count: int = 6, allow_decimals: bool = True
) -> List[Decimal]:
    """Calculate the ticks of an interval, the count of ticks will be guaranteed"""
    # More than two ticks should be returned
    count = max(tick_count, 2)
    minimum, maximum = sorted(domain)
    if minimum == maximum:
        values = get_tick_of_single_value(minimum, tick_count, allow_decimals)
    else:
        step, tick_min, tick_max = calculate_step(
            minimum, maximum, count, allow_decimals
        )
        values = []
        value = tick_min
        end = tick_max + Decimal("0.1") * step
        while value < end:
            values.append(value)
            value += step
    return values if domain[0] <= domain[1] else list(reversed(values))
