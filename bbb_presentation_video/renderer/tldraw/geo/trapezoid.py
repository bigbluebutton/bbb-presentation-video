# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from random import Random
from typing import List, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    Trapezoid,
)
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    apply_geo_fill,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    finalize_geo_path,
)


def trapezoid_stroke_points(id: str, shape: Trapezoid) -> List[StrokePoint]:
    random = Random(id)
    size = shape.size

    width = size.width
    height = size.height

    top_width = width * 0.6
    x_offset = (width - top_width) / 2

    stroke_width = STROKE_WIDTHS[shape.style.size]

    # Corners with random offsets
    variation = stroke_width * 0.75

    tl = (
        x_offset + random.uniform(-variation, variation),
        random.uniform(-variation, variation),
    )
    tr = (
        x_offset + top_width + random.uniform(-variation, variation),
        0 + random.uniform(-variation, variation),
    )
    br = (
        width + random.uniform(-variation, variation),
        height + random.uniform(-variation, variation),
    )
    bl = (
        random.uniform(-variation, variation),
        height + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 3)
    # Number of points per side
    # Insert each line by the corner radii and let the freehand algo
    # interpolate points for the corners.
    lines = [
        vec.points_between(tl, tr, 32),
        vec.points_between(tr, br, 32),
        vec.points_between(br, bl, 32),
        vec.points_between(bl, tl, 32),
    ]
    lines = lines[rm:] + lines[0:rm]

    # For the final points, include the first half of the first line again,
    # so that the line wraps around and avoids ending on a sharp corner.
    # This has a bit of finesse and magic—if you change the points between
    # function, then you'll likely need to change this one too.
    # TODO: It actually includes the whole first line again, not just half?
    points = [*lines[0], *lines[1], *lines[2], *lines[3], *lines[0]]

    return perfect_freehand.get_stroke_points(
        points, size=stroke_width, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_trapezoid(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: Trapezoid
) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = trapezoid_stroke_points(id, shape)

    if style.isFilled:
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
        apply_geo_fill(ctx, style)

    stroke_outline_points = perfect_freehand.get_stroke_outline_points(
        stroke_points,
        size=stroke_width,
        thinning=0.65,
        smoothing=1,
        simulate_pressure=False,
        last=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)

    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
    ctx.fill_preserve()
    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def dash_trapezoid(ctx: cairo.Context[CairoSomeSurface], shape: Trapezoid) -> None:
    style = shape.style
    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    top_width = width * 0.6
    x_offset = (width - top_width) / 2

    points = [
        Position(x_offset, 0),
        Position(top_width + x_offset, 0),
        Position(width, height),
        Position(0, height),
    ]

    finalize_geo_path(ctx, points, style)


def finalize_trapezoid(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: Trapezoid
) -> None:
    print(f"\tTldraw: Finalizing Trapezoid: {id}")

    style = shape.style

    ctx.rotate(shape.rotation)

    if style.dash is DashStyle.DRAW:
        draw_trapezoid(ctx, id, shape)
    else:
        dash_trapezoid(ctx, shape)

    finalize_v2_label(ctx, shape)
