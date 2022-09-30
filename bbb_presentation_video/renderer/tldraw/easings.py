# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import cos, pi


def ease_in_out_sine(t: float) -> float:
    return -(cos(pi * t) - 1) / 2
