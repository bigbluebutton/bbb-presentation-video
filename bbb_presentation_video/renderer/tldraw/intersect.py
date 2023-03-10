# SPDX-FileCopyrightText: 2021 Stephen Ruiz Ltd
# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: MIT

from math import sqrt
from typing import List, Sequence, Tuple

import attr

from bbb_presentation_video.renderer.tldraw import vec

S = Sequence[float]
V = Tuple[float, float]


@attr.s(order=False, slots=True, auto_attribs=True, init=False)
class Intersection:
    did_intersect: bool
    message: str
    points: List[V]

    def __init__(self, message: str, *points: V) -> None:
        self.did_intersect = len(points) > 0
        self.message = message
        self.points = list(points)


def intersect_line_segment_circle(a1: S, a2: S, c: S, r: float) -> Intersection:
    """Find the intersections between a line segment and a circle."""
    a = (a2[0] - a1[0]) * (a2[0] - a1[0]) + (a2[1] - a1[1]) * (a2[1] - a1[1])
    b = 2 * ((a2[0] - a1[0]) * (a1[0] - c[0]) + (a2[1] - a1[1]) * (a1[1] - c[1]))
    cc = (
        c[0] * c[0]
        + c[1] * c[1]
        + a1[0] * a1[0]
        + a1[1] * a1[1]
        - 2 * (c[0] * a1[0] + c[1] * a1[1])
        - r * r
    )

    deter = b * b - 4 * a * cc

    if deter < 0:
        return Intersection("outside")

    if deter == 0:
        return Intersection("tangent")

    e = sqrt(deter)
    u1 = (-b + e) / (2 * a)
    u2 = (-b - e) / (2 * a)
    if (u1 < 0 or u1 > 1) and (u2 < 0 or u2 > 1):
        if (u1 < 0 and u2 < 0) or (u1 > 1 and u2 > 1):
            return Intersection("outside")
        else:
            return Intersection("inside")

    results: List[Tuple[float, float]] = []
    if 0 <= u1 and u1 <= 1:
        results.append(vec.lrp(a1, a2, u1))
    if 0 <= u2 and u2 <= 1:
        results.append(vec.lrp(a1, a2, u2))

    return Intersection("intersection", *results)


def intersect_circle_line_segment(c: S, r: float, a1: S, a2: S) -> Intersection:
    """Find the intersections between a circle and a line segment."""
    return intersect_line_segment_circle(a1, a2, c, r)


def intersect_circle_circle(c1: S, r1: float, c2: S, r2: float) -> Intersection:
    """Find the intersections between a circle and a circle."""
    dx = c2[0] - c1[0]
    dy = c2[1] - c1[1]

    d = sqrt(dx * dx + dy * dy)
    x = (d * d - r2 * r2 + r1 * r1) / (2 * d)
    y = sqrt(r1 * r1 - x * x)

    dx /= d
    dy /= d

    return Intersection(
        "intersection",
        (c1[0] + dx * x - dy * y, c1[1] + dy * x + dx * y),
        (c1[0] + dx * x + dy * y, c1[1] + dy * x - dx * y),
    )
