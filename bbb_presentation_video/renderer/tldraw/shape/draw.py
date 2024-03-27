# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import tau
from typing import Tuple, TypeVar, cast

import cairo
import perfect_freehand

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.easings import ease_in_quad, ease_out_sine
from bbb_presentation_video.renderer.tldraw.shape import DrawShape, apply_shape_rotation
from bbb_presentation_video.renderer.tldraw.utils import (
    FILLS,
    STROKE_WIDTHS,
    STROKES,
    COLORS,
    DashStyle,
    FillStyle,
    ColorStyle,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    draw_stroke_points,
    pattern_fill,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def finalize_draw(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: DrawShape
) -> None:
    print(f"\tTldraw: Finalizing Draw: {id}")

    apply_shape_rotation(ctx, shape)

    points = shape.points
    style = shape.style
    is_complete = shape.isComplete
    stroke = STROKES[style.color]
    fill = FILLS[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    # For very short lines, draw a point instead of a line
    size = shape.size
    very_small = size.width <= stroke_width / 2 and size.height <= stroke_width < 2

    if very_small:
        sw = 1 + stroke_width
        ctx.arc(0, 0, sw, 0, tau)
        ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
        ctx.fill_preserve()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(1)
        ctx.stroke()
        return

    should_fill = (
        style.isFilled
        and len(points) > 3
        and vec.dist(points[0], points[-1]) < stroke_width * 2
    ) or (style.isClosed and style.fill is not FillStyle.NONE)

    stroke_points = draw_stroke_points(shape.points, stroke_width, is_complete)

    if should_fill:
        # Shape is configured to be filled, and is fillable
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        if style.fill is FillStyle.SEMI:
            fill = COLORS[ColorStyle.SEMI]
            ctx.set_source_rgba(fill.r, fill.g, fill.b, style.opacity)
        elif style.fill is FillStyle.PATTERN:
            pattern = pattern_fill(fill)
            ctx.set_source(pattern)
        else:
            # Solid fill
            ctx.set_source_rgba(fill.r, fill.g, fill.b, style.opacity)

        ctx.fill()

    if style.dash is DashStyle.DRAW:
        # Smoothed freehand drawing style
        simulate_pressure = False
        if len(shape.points[0]) == 2:
            simulate_pressure = True
        else:
            first_point = shape.points[0]
            if first_point[2] == 0.5:
                simulate_pressure = True

        stroke_outline_points = perfect_freehand.get_stroke_outline_points(
            stroke_points,
            size=1 + stroke_width * 1.5,
            thinning=0.65,
            smoothing=0.65,
            simulate_pressure=simulate_pressure,
            last=is_complete,
            easing=ease_out_sine if simulate_pressure else ease_in_quad,
        )

        draw_smooth_path(ctx, stroke_outline_points)

        ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
        ctx.fill_preserve()

        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(stroke_width / 2)
        ctx.stroke()

    else:
        # Normal stroked path, possibly with dash or dot pattern
        if style.dash is DashStyle.DOTTED:
            ctx.set_dash([0, stroke_width * 4])
        elif style.dash is DashStyle.DASHED:
            ctx.set_dash([stroke_width * 4, stroke_width * 4])

        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(1 + stroke_width * 1.5)
        ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
        ctx.stroke()
