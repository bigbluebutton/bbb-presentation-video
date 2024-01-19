# SPDX-FileCopyrightText: 2021 Stephen Ruiz Ltd
# SPDX-FileCopyrightText: 2022 Calvin Walton
#
# SPDX-License-Identifier: MIT

from math import atan2, cos, hypot, sin
from typing import List, Sequence, Tuple

from bbb_presentation_video.events.helpers import Position

S = Sequence[float]
V = Tuple[float, float]


def add(a: S, b: S) -> V:
    """Add vectors."""
    return (a[0] + b[0], a[1] + b[1])


def sub(a: S, b: S) -> V:
    """Subtract vectors."""
    return (a[0] - b[0], a[1] - b[1])


def vec(a: S, b: S) -> V:
    """Get the vector from vectors A to B."""
    return (b[0] - a[0], b[1] - a[1])


def mul(a: S, n: float) -> V:
    """Vector multiplication by a scalar."""
    return (a[0] * n, a[1] * n)


def div(a: S, n: float) -> V:
    """Vector division by a scalar."""
    return (a[0] / n, a[1] / n)


def per(a: S) -> V:
    """Perpendicular rotation of a vector A."""
    return (a[1], -a[0])


def vlen(a: S) -> float:
    """Length of the vector."""
    return hypot(a[0], a[1])


def uni(a: S) -> V:
    """Get normalized / unit vector."""
    return div(a, vlen(a))


def dist(a: S, b: S) -> float:
    """Dist length from a to b."""
    return hypot(a[1] - b[1], a[0] - b[0])


def angle(A: S, B: S) -> float:
    """Angle between vector A and vector B in radians."""
    return atan2(B[1] - A[1], B[0] - A[0])


def med(a: S, b: S) -> V:
    """Mean between two vectors or mid vector between two vectors."""
    return mul(add(a, b), 0.5)


def rot_with(A: S, C: S, r: float = 0) -> V:
    """Rotate a vector around another vector by r (radians)"""
    if r == 0:
        return (A[0], A[1])

    s = sin(r)
    c = cos(r)

    px = A[0] - C[0]
    py = A[1] - C[1]

    nx = px * c - py * s
    ny = px * s + py * c

    return (nx + C[0], ny + C[1])


def is_equal(a: S, b: S) -> bool:
    """Check if two vectors are identical."""
    return a[0] == b[0] and a[1] == b[1]


def lrp(a: S, b: S, t: float) -> V:
    """Interpolate vector A to B with a scalar t."""
    return add(a, mul(sub(b, a), t))


def to_fixed(a: S) -> V:
    """Round a vector to two decimal places."""
    return (round(a[0], ndigits=2), round(a[1], ndigits=2))


def nudge(a: S, b: S, d: float) -> V:
    """Push a point A towards point B by a given distance."""
    if is_equal(a, b):
        return (a[0], a[1])
    return add(a, mul(uni(sub(b, a)), d))


def nudge_at_angle(A: S, a: float, d: float) -> V:
    """Push a point in a given angle by a given distance."""
    return (cos(a) * d + A[0], sin(a) * d + A[1])


def points_between(a: S, b: S, steps: int = 6) -> List[Tuple[float, float, float]]:
    """Get an array of points (with simulated pressure) between two points."""
    points: List[Tuple[float, float, float]] = []
    for i in range(0, steps):
        t = i / (steps - 1)
        k = min(1, 0.5 + abs(0.5 - t))
        points.append((*lrp(a, b, t), k))
    return points


def to_position(a: S) -> Position:
    """Convert a vector to a Position."""
    return Position(a[0], a[1])


def from_angle(r: float, length: float) -> Tuple[float, float]:
    return (cos(r) * length, sin(r) * length)


def is_left(a: S, b: S, c: S) -> bool:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0
