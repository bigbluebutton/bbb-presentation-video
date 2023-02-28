# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import cos, pi, sin
from random import Random
from typing import List, Tuple, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.renderer.tldraw import easings
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
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    get_perfect_dash_props,
    perimeter_of_ellipse,
)
from bbb_presentation_video.renderer.whiteboard import BEZIER_CIRCLE_MAGIC


def draw_stroke_points(id: str, shape: EllipseShape) -> Tuple[List[StrokePoint], float]:
    stroke_width = STROKE_WIDTHS[shape.style.size]
    random = Random(id)
    variation = stroke_width * 2
    rx = shape.radius[0] + random.uniform(-variation, variation)
    ry = shape.radius[1] + random.uniform(-variation, variation)
    perimeter = perimeter_of_ellipse(rx, ry)
    points: List[Tuple[float, float, float]] = []
    start = pi + pi + random.uniform(-1, 1)
    extra = random.random()
    count = int(max(16, perimeter / 10))
    for i in range(0, count):
        t = easings.ease_in_out_sine(i / (count + 1))
        rads = start * 2 + pi * (2 + extra) * t
        c = cos(rads)
        s = sin(rads)
        points.append(
            (
                rx * c + shape.radius[0],
                ry * s + shape.radius[1],
                t + random.random(),
            )
        )

    return (
        perfect_freehand.get_stroke_points(
            points, size=2 + stroke_width * 2, streamline=0
        ),
        perimeter,
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def draw_ellipse(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: EllipseShape
) -> None:
    style = shape.style

    stroke_points, perimeter = draw_stroke_points(id, shape)

    if shape.style.isFilled:
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill()

    stroke_outline_points = perfect_freehand.get_stroke_outline_points(
        stroke_points,
        size=2 + STROKE_WIDTHS[style.size] * 2,
        thinning=0.618,
        taper_end=perimeter / 8,
        taper_start=perimeter / 12,
        simulate_pressure=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)

    ctx.set_source_rgb(*STROKES[style.color])
    ctx.fill_preserve()
    ctx.set_line_width(STROKE_WIDTHS[style.size])
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def dash_ellipse(
    ctx: "cairo.Context[CairoSomeSurface]", shape: EllipseShape
) -> None:
    style = shape.style
    stroke_width = STROKE_WIDTHS[style.size] * 1.618
    radius_x = shape.radius[0]
    radius_y = shape.radius[1]

    sw = 1 + stroke_width
    rx = max(0, radius_x - sw / 2)
    ry = max(0, radius_y - sw / 2)
    perimeter = perimeter_of_ellipse(rx, ry)
    dash_array, dash_offset = get_perfect_dash_props(
        perimeter * 2 if perimeter < 64 else perimeter,
        stroke_width,
        style.dash,
        snap=4,
    )

    # Draw a bezier approximation to the ellipse. Cairo's arc function
    # doesn't deal well with degenerate (0-height/width) ellipses because
    # of the scaling required.
    ctx.translate(radius_x, radius_y)  # math is easier from center of ellipse
    ctx.move_to(-rx, 0)
    ctx.curve_to(-rx, -ry * BEZIER_CIRCLE_MAGIC, -rx * BEZIER_CIRCLE_MAGIC, -ry, 0, -ry)
    ctx.curve_to(rx * BEZIER_CIRCLE_MAGIC, -ry, rx, -ry * BEZIER_CIRCLE_MAGIC, rx, 0)
    ctx.curve_to(rx, ry * BEZIER_CIRCLE_MAGIC, rx * BEZIER_CIRCLE_MAGIC, ry, 0, ry)
    ctx.curve_to(-rx * BEZIER_CIRCLE_MAGIC, ry, -rx, ry * BEZIER_CIRCLE_MAGIC, -rx, 0)
    ctx.close_path()

    if style.isFilled:
        ctx.set_source_rgb(*FILLS[style.color])
        ctx.fill_preserve()

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(*STROKES[style.color])
    ctx.stroke()


def finalize_ellipse(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: EllipseShape
) -> None:
    print(f"\tTldraw: Finalizing Ellipse: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style

    if style.dash is DashStyle.DRAW:
        draw_ellipse(ctx, id, shape)
    else:
        dash_ellipse(ctx, shape)

    finalize_label(ctx, shape)
