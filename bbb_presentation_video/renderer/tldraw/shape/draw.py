# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import pi, sin
from typing import List, Optional

import cairo
import perfect_freehand

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import DrawShape, apply_shape_rotation
from bbb_presentation_video.renderer.tldraw.utils import (
    FILLS,
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    draw_stroke_points,
    get_bounds_from_points,
)


def freehand_draw_easing(t: float) -> float:
    return sin(t * pi) / 2


def finalize_draw(ctx: cairo.Context, id: str, shape: DrawShape) -> None:
    print(f"\tTldraw: Finalizing Draw: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style
    points = shape.points
    stroke_color = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    bounds = shape.cached_bounds
    if bounds is None:
        bounds = shape.cached_bounds = get_bounds_from_points(points)

    if bounds.width <= stroke_width / 2 and bounds.height <= stroke_width < 2:
        # Shape is too small, draw a circle
        ctx.arc(0, 0, 1 + stroke_width, 0, 2 * pi)
        ctx.set_source_rgb(*stroke_color)
        ctx.fill_preserve()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(stroke_width / 2)
        ctx.stroke()
        return

    stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None

    should_fill = (
        style.isFilled
        and len(shape.points) > 3
        and vec.dist(points[0], points[-1]) < stroke_width * 2
    )

    if should_fill:
        # Shape is configured to be filled, and is fillable
        cached_path = shape.cached_path
        if cached_path is not None:
            ctx.append_path(cached_path)
        else:
            stroke_points = draw_stroke_points(points, stroke_width, shape.isComplete)
            draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
            shape.cached_path = ctx.copy_path()
        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill()

    if style.dash is DashStyle.DRAW:
        # Smoothed freehand drawing style
        cached_outline_path = shape.cached_outline_path
        if cached_outline_path is not None:
            ctx.append_path(cached_outline_path)
        else:
            if stroke_points is None:
                stroke_points = draw_stroke_points(
                    points, stroke_width, shape.isComplete
                )
            stroke_outline_points = perfect_freehand.get_stroke_outline_points(
                stroke_points,
                size=1 + stroke_width * 1.5,
                thinning=0.65,
                smoothing=0.65,
                simulate_pressure=True,
                last=shape.isComplete,
                easing=freehand_draw_easing,
            )
            draw_smooth_path(ctx, stroke_outline_points)
            shape.cached_outline_path = ctx.copy_path()
        ctx.set_source_rgb(*stroke_color)
        ctx.fill_preserve()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(stroke_width / 2)
        ctx.stroke()
        return

    elif style.dash is DashStyle.DOTTED:
        ctx.set_dash([0, stroke_width * 4])
    elif style.dash is DashStyle.DASHED:
        ctx.set_dash([stroke_width * 4, stroke_width * 4])

    # Normal stroked path, possibly with dash or dot pattern
    cached_path = shape.cached_path
    if cached_path is not None:
        ctx.append_path(cached_path)
    else:
        stroke_points = draw_stroke_points(points, stroke_width, shape.isComplete)
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
        shape.cached_path = ctx.copy_path()
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_line_width(1 + stroke_width * 1.5)
    ctx.set_source_rgb(*stroke_color)
    ctx.stroke()
