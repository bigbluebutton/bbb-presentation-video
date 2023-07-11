# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import cos, pi, sin, tau
from random import Random
from typing import List, Tuple, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.renderer.tldraw.easings import ease_in_out_sine
from bbb_presentation_video.renderer.tldraw.shape import (
    EllipseShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.shape.text import finalize_label
from bbb_presentation_video.renderer.tldraw.utils import (
    FILLS,
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    Style,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    get_perfect_dash_props,
    perimeter_of_ellipse,
)
from bbb_presentation_video.renderer.utils import cairo_draw_ellipse


def draw_stroke_points(
    id: str, radius: Tuple[float, float], style: Style
) -> Tuple[List[StrokePoint], float]:
    stroke_width = STROKE_WIDTHS[style.size]
    random = Random(id)
    variation = stroke_width * 2
    rx = radius[0] + random.uniform(-variation, variation)
    ry = radius[1] + random.uniform(-variation, variation)
    perimeter = perimeter_of_ellipse(rx, ry)
    points: List[Tuple[float, float, float]] = []
    start = random.uniform(0, tau)
    extra = random.random()
    count = int(max(16, perimeter / 10))
    for i in range(0, count):
        t = ease_in_out_sine(i / (count + 1))
        rads = start * 2 + pi * (2 + extra) * t
        c = cos(rads)
        s = sin(rads)
        points.append(
            (
                rx * c + radius[0],
                ry * s + radius[1],
                t + random.random(),
            )
        )

    return (
        perfect_freehand.get_stroke_points(
            points, size=1 + stroke_width * 2, streamline=0
        ),
        perimeter,
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_ellipse(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: EllipseShape
) -> None:
    radius = shape.radius
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]
    fill = FILLS[style.color]

    stroke_points, perimeter = draw_stroke_points(id, radius, style)

    if style.isFilled:
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill()

    stroke_outline_points = perfect_freehand.get_stroke_outline_points(
        stroke_points,
        size=1 + stroke_width * 2,
        thinning=0.618,
        taper_end=perimeter / 8,
        taper_start=perimeter / 12,
        simulate_pressure=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)

    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.fill_preserve()
    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def dash_ellipse(ctx: cairo.Context[CairoSomeSurface], shape: EllipseShape) -> None:
    radius = shape.radius
    style = shape.style
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]
    fill = FILLS[style.color]

    sw = 1 + stroke_width * 1.618
    rx = max(0, radius[0] - sw / 2)
    ry = max(0, radius[1] - sw / 2)
    perimeter = perimeter_of_ellipse(rx, ry)
    dash_array, dash_offset = get_perfect_dash_props(
        perimeter * 2 if perimeter < 64 else perimeter,
        stroke_width * 1.618,
        style.dash,
        snap=4,
    )

    cairo_draw_ellipse(ctx, radius[0], radius[1], radius[0], radius[1])

    if style.isFilled:
        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill_preserve()

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.stroke()


def finalize_ellipse(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: EllipseShape
) -> None:
    print(f"\tTldraw: Finalizing Ellipse: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style

    if style.dash is DashStyle.DRAW:
        draw_ellipse(ctx, id, shape)
    else:
        dash_ellipse(ctx, shape)

    finalize_label(ctx, shape)
