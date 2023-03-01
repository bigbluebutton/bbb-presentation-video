# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import hypot
from random import Random
from typing import List, Optional, Tuple, TypeVar

import cairo
from attr import astuple
from perfect_freehand import get_stroke
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.easings import ease_out_quad
from bbb_presentation_video.renderer.tldraw.intersect import (
    intersect_circle_line_segment,
)
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    Decoration,
    Style,
    draw_smooth_path,
    get_perfect_dash_props,
)


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


def freehand_arrow_shaft(
    ctx: "cairo.Context[CairoSomeSurface]",
    id: str,
    style: Style,
    start: Tuple[float, float],
    end: Tuple[float, float],
    deco_start: Optional[Decoration],
    deco_end: Optional[Decoration],
) -> None:
    random = Random(id)
    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618
    start_point = start if deco_start is None else vec.nudge(start, end, stroke_width)
    end_point = end if deco_end is None else vec.nudge(end, start, stroke_width)

    stroke = get_stroke(
        [start_point, end_point],
        size=stroke_width,
        thinning=0.618 + random.uniform(-0.2, 0.2),
        easing=ease_out_quad,
        simulate_pressure=True,
        streamline=0,
        last=True,
    )
    draw_smooth_path(ctx, stroke, closed=True)
    ctx.set_source_rgb(*STROKES[style.color])
    ctx.fill_preserve()
    ctx.set_line_width(sw / 2)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def straight_arrow_head(
    ctx: "cairo.Context[CairoSomeSurface]",
    a: Tuple[float, float],
    b: Tuple[float, float],
    r: float,
) -> None:
    ints = intersect_circle_line_segment(a, r, a, b).points
    if len(ints) == 0:
        print("\t\tCould not find an intersection for the arrow head.")
        left = a
        right = a
    else:
        int = ints[0]


def straight_arrow(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: ArrowShape
) -> None:
    print("\t\tDrawing a straight arrow")
    style = shape.style
    start = astuple(shape.handles.start)
    end = astuple(shape.handles.end)
    deco_start = shape.decorations.start
    deco_end = shape.decorations.end
    arrow_dist = vec.dist(start, end)
    if arrow_dist < 2:
        return
    stroke_width = STROKE_WIDTHS[shape.style.size]
    sw = 1 + stroke_width * 1.618
    # Path between start and end points
    if style.dash is DashStyle.DRAW:
        freehand_arrow_shaft(ctx, id, shape.style, start, end, deco_start, deco_end)
    else:
        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_source_rgb(*STROKES[style.color])
        ctx.move_to(*start)
        ctx.line_to(*end)
        dash_array, dash_offset = get_perfect_dash_props(
            arrow_dist, stroke_width * 1.618, style.dash, snap=2, outset=False
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()
    # Arrowheads
    arrow_head_len = min(arrow_dist / 3, stroke_width * 8)
    if deco_start is Decoration.ARROW:
        straight_arrow_head(ctx, start, end, arrow_head_len)
    if deco_end is Decoration.ARROW:
        straight_arrow_head(ctx, end, start, arrow_head_len)


def curved_arrow(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: ArrowShape
) -> None:
    ...


def finalize_arrow(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: ArrowShape
) -> None:
    print(f"\tTldraw: Finalizing Arrow: {id}")

    apply_shape_rotation(ctx, shape)

    handles = shape.handles
    is_straight_line = (
        vec.dist(
            astuple(handles.bend),
            vec.to_fixed(vec.med(astuple(handles.start), astuple(handles.end))),
        )
        < 1
    )
    if is_straight_line:
        straight_arrow(ctx, id, shape)
    else:
        curved_arrow(ctx, id, shape)
