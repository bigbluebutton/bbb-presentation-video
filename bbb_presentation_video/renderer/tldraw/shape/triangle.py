# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import hypot
from random import Random
from typing import List, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.events.helpers import Position, Size
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


def triangle_centroid(size: Size) -> Position:
    w, h = size
    return (Position(w / 2, 0) + Position(w, h) + Position(0, h)) / 3


def triangle_stroke_points(id: str, shape: TriangleShape) -> List[StrokePoint]:
    random = Random(id)
    size = shape.size
    stroke_width = STROKE_WIDTHS[shape.style.size]

    # Corners with random offsets
    variation = stroke_width * 0.75
    t = (
        size.width / 2 + random.uniform(-variation, variation),
        random.uniform(-variation, variation),
    )
    br = (
        size.width + random.uniform(-variation, variation),
        size.height + random.uniform(-variation, variation),
    )
    bl = (
        random.uniform(-variation, variation),
        size.height + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 3)
    # Number of points per side
    # Insert each line by the corner radii and let the freehand algo
    # interpolate points for the corners.
    lines = [
        vec.points_between(t, br, 32),
        vec.points_between(br, bl, 32),
        vec.points_between(bl, t, 32),
    ]
    lines = lines[rm:] + lines[0:rm]

    # For the final points, include the first half of the first line again,
    # so that the line wraps around and avoids ending on a sharp corner.
    # This has a bit of finesse and magic—if you change the points between
    # function, then you'll likely need to change this one too.
    # TODO: It actually includes the whole first line again, not just half?
    points = [*lines[0], *lines[1], *lines[2], *lines[0]]

    return perfect_freehand.get_stroke_points(
        points, size=stroke_width, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_triangle(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TriangleShape
) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]
    fill = FILLS[style.color]

    stroke_points = triangle_stroke_points(id, shape)

    if style.isFilled:
        ctx.save()
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill()
        ctx.restore()

    stroke_outline_points = perfect_freehand.get_stroke_outline_points(
        stroke_points,
        size=stroke_width,
        thinning=0.65,
        smoothing=1,
        simulate_pressure=False,
        last=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)

    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.fill_preserve()
    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def dash_triangle(ctx: cairo.Context[CairoSomeSurface], shape: TriangleShape) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size] * 1.618
    fill = FILLS[style.color]

    sw = 1 + stroke_width
    w = max(0, shape.size.width - sw / 2)
    h = max(0, shape.size.height - sw / 2)

    side_width = hypot(w / 2, h)

    if style.isFilled:
        ctx.save()
        ctx.move_to(w / 2, 0)
        ctx.line_to(w, h)
        ctx.line_to(0, h)
        ctx.close_path()
        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill()
        ctx.restore()

    strokes = [
        (Position(w / 2, 0), Position(w, h), side_width),
        (Position(w, h), Position(0, h), w),
        (Position(0, h), Position(w / 2, 0), side_width),
    ]
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    for start, end, length in strokes:
        ctx.move_to(start.x, start.y)
        ctx.line_to(end.x, end.y)
        dash_array, dash_offset = get_perfect_dash_props(
            length, stroke_width, style.dash
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()


def finalize_triangle(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TriangleShape
) -> None:
    print(f"\tTldraw: Finalizing Triangle: {id}")

    style = shape.style
    size = shape.size

    apply_shape_rotation(ctx, shape)

    if style.dash is DashStyle.DRAW:
        draw_triangle(ctx, id, shape)
    else:
        dash_triangle(ctx, shape)

    center = Position(size / 2)
    centeroid = triangle_centroid(size)
    offset_y = (centeroid.y - center.y) * 0.72
    offset = shape.label_offset() + Position(0, offset_y)
    finalize_label(ctx, shape, offset=offset)
