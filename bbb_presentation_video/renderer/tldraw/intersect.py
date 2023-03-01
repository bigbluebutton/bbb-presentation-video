# SPDX-FileCopyrightText: 2021 Stephen Ruiz Ltd
# SPDX-FileCopyrightText: 2022 Calvin Walton
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
        self.__attrs_init__(
            did_intersect=len(points) > 0, message=message, points=list(points)
        )


def intersect_line_segment_circle(a1: S, a2: S, c: S, r: float) -> Intersection:
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
    return intersect_line_segment_circle(a1, a2, c, r)
