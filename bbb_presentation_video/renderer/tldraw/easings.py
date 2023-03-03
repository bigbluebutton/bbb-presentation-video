# SPDX-FileCopyrightText: 2021 Stephen Ruiz Ltd
# SPDX-FileCopyrightText: 2022 Calvin Walton
#
# SPDX-License-Identifier: MIT

from math import cos, pi, sin


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return t * (2 - t)


def ease_in_out_cubic(t: float) -> float:
    return 4 * t * t * t if t < 0.5 else (t - 1) * (2 * t - 2) * (2 * t - 2) + 1


def ease_out_sine(t: float) -> float:
    return sin((t * pi) / 2)


def ease_in_out_sine(t: float) -> float:
    return -(cos(pi * t) - 1) / 2
