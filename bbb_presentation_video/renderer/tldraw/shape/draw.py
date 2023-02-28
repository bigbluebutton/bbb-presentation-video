# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import pi, sin
from typing import Tuple, TypeVar, cast

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
)


def simulate_pressure_easing(t: float) -> float:
    return sin(t * pi) / 2


def real_pressure_easing(t: float) -> float:
    return t * t


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def finalize_draw(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: DrawShape
) -> None:
    print(f"\tTldraw: Finalizing Draw: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style
    size = shape.size
    points = shape.points
    stroke_color = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    if size.width <= stroke_width / 2 and size.height <= stroke_width < 2:
        # Shape is too small, draw a circle
        ctx.arc(0, 0, 1 + stroke_width, 0, 2 * pi)
        ctx.set_source_rgb(*stroke_color)
        ctx.fill_preserve()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(stroke_width / 2)
        ctx.stroke()
        return

    should_fill = (
        style.isFilled
        and len(shape.points) > 3
        and vec.dist(points[0], points[-1]) < stroke_width * 2
    )

    stroke_points = draw_stroke_points(
        shape.points, STROKE_WIDTHS[style.size], shape.isComplete
    )

    if should_fill:
        # Shape is configured to be filled, and is fillable
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill()

    if style.dash is DashStyle.DRAW:
        # Smoothed freehand drawing style
        simulate_pressure = False
        if len(shape.points[0]) == 2:
            simulate_pressure = True
        else:
            # Work around python/mypy#1178
            first_point = cast(Tuple[float, float, float], shape.points[0])
            if first_point[2] == 0.5:
                simulate_pressure = True

        stroke_outline_points = perfect_freehand.get_stroke_outline_points(
            stroke_points,
            size=1 + STROKE_WIDTHS[shape.style.size] * 1.5,
            thinning=0.65,
            smoothing=0.65,
            simulate_pressure=simulate_pressure,
            last=shape.isComplete,
            easing=(
                simulate_pressure_easing if simulate_pressure else real_pressure_easing
            ),
        )
        draw_smooth_path(ctx, stroke_outline_points)

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
    draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_line_width(1 + stroke_width * 1.5)
    ctx.set_source_rgb(*stroke_color)
    ctx.stroke()
