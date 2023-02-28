# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import hypot
from random import Random
from typing import Tuple, TypeVar

import cairo
from attr import astuple

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import ArrowShape
from bbb_presentation_video.renderer.tldraw.utils import STROKE_WIDTHS


def bend_point(shape: ArrowShape) -> Tuple[float, float]:
    start_point = astuple(shape.handles.start)
    end_point = astuple(shape.handles.end)

    dist = vec.dist(start_point, end_point)
    mid_point = vec.med(start_point, end_point)
    bend_dist = (dist / 2) * shape.bend
    u = vec.uni(vec.vec(start_point, end_point))

    point: Tuple[float, float]
    if bend_dist < 10:
        point = mid_point
    else:
        point = vec.add(mid_point, vec.mul(vec.per(u), bend_dist))
    return point


def circle_from_three_points(
    A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]
) -> Tuple[float, float, float]:
    (x1, y1) = A
    (x2, y2) = B
    (x3, y3) = C

    a = x1 * (y2 - y3) - y1 * (x2 - x3) + x2 * y3 - x3 * y2

    b = (
        (x1 * x1 + y1 * y1) * (y3 - y2)
        + (x2 * x2 + y2 * y2) * (y1 - y3)
        + (x3 * x3 + y3 * y3) * (y2 - y1)
    )

    c = (
        (x1 * x1 + y1 * y1) * (x2 - x3)
        + (x2 * x2 + y2 * y2) * (x3 - x1)
        + (x3 * x3 + y3 * y3) * (x1 - x2)
    )

    x = -b / (2 * a)

    y = -c / (2 * a)

    return (x, y, hypot(x - x1, y - y1))


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def freehand_arrow_shaft_stroke_points(id: str, shape: ArrowShape) -> None:
    random = Random(id)
    stroke_width = STROKE_WIDTHS[shape.style.size]
    ...


def finalize_arrow(ctx: "cairo.Context[CairoSomeSurface]", shape: ArrowShape) -> None:
    ...
