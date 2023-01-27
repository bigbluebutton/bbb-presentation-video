# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import hypot
from random import Random
from typing import List, Optional, Tuple, TypeVar

import cairo
import perfect_freehand

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    TriangleShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.shape.text import finalize_label
from bbb_presentation_video.renderer.tldraw.utils import (
    FILLS,
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    get_perfect_dash_props,
)


def triangle_stroke_points(
    id: str, shape: TriangleShape
) -> List[perfect_freehand.types.StrokePoint]:
    random = Random(id)
    print(f"\tRandom state: {random.random()}")
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    # Corners
    variation = sw * 0.75
    t = (
        w / 2 + random.uniform(-variation, variation),
        random.uniform(-variation, variation),
    )
    br = (
        w + random.uniform(-variation, variation),
        h + random.uniform(-variation, variation),
    )
    bl = (
        random.uniform(-variation, variation),
        h + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 3)

    lines = [
        vec.points_between(t, br, 32),
        vec.points_between(br, bl, 32),
        vec.points_between(bl, t, 32),
    ]
    lines = lines[rm:] + lines[0:rm]

    points: List[Tuple[float, float, float]] = [
        *lines[0],
        *lines[1],
        *lines[2],
        *lines[0],
    ]

    return perfect_freehand.get_stroke_points(
        points, size=sw, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def finalize_draw_triangle(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: TriangleShape
) -> None:
    style = shape.style

    stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None

    if style.isFilled:
        cached_path = shape.cached_path
        if cached_path is not None:
            ctx.append_path(cached_path)
        else:
            stroke_points = triangle_stroke_points(id, shape)
            draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
            shape.cached_path = ctx.copy_path()
        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill()

    cached_outline_path = shape.cached_outline_path
    if cached_outline_path is not None:
        ctx.append_path(cached_outline_path)
    else:
        if stroke_points is None:
            stroke_points = triangle_stroke_points(id, shape)
        stroke_outline_points = perfect_freehand.get_stroke_outline_points(
            stroke_points,
            size=STROKE_WIDTHS[style.size],
            thinning=0.65,
            smoothing=1,
            simulate_pressure=False,
            last=True,
        )
        draw_smooth_path(ctx, stroke_outline_points, closed=True)
        shape.cached_outline_path = ctx.copy_path()

    ctx.set_source_rgb(*STROKES[style.color])
    ctx.fill_preserve()
    ctx.set_line_width(STROKE_WIDTHS[style.size])
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def finalize_dash_triangle(
    ctx: "cairo.Context[CairoSomeSurface]", shape: TriangleShape
) -> None:
    style = shape.style
    stroke_width = STROKE_WIDTHS[style.size] * 1.618

    sw = 1 + stroke_width
    w = max(0, shape.size.width - sw / 2)
    h = max(0, shape.size.height - sw / 2)

    side_width = hypot(w / 2, h)

    if style.isFilled:
        ctx.move_to(w / 2, 0)
        ctx.line_to(w, h)
        ctx.line_to(0, h)
        ctx.close_path()
        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill()

    strokes = [
        ((w / 2, 0), (w, h), side_width),
        ((w, h), (0, h), w),
        ((0, h), (w / 2, 0), side_width),
    ]
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(*STROKES[style.color])
    for start, end, length in strokes:
        dash_array, dash_offset = get_perfect_dash_props(
            length, stroke_width, style.dash
        )
        ctx.move_to(*start)
        ctx.line_to(*end)
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()


def finalize_triangle(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: TriangleShape
) -> None:
    print(f"\tTldraw: Finalizing Triangle: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style

    if style.dash is DashStyle.DRAW:
        finalize_draw_triangle(ctx, id, shape)
    else:
        finalize_dash_triangle(ctx, shape)

    finalize_label(ctx, shape)
