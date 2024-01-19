# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from random import Random
from typing import List, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    Rhombus,
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


def rhombus_stroke_points(id: str, shape: Rhombus) -> List[StrokePoint]:
    random = Random(id)
    size = shape.size

    width = size.width
    height = size.height

    x_offset = min(width * 0.38, height * 0.38)
    stroke_width = STROKE_WIDTHS[shape.style.size]

    # Corners with random offsets
    variation = stroke_width * 0.75

    tl = (
        x_offset + random.uniform(-variation, variation),
        random.uniform(-variation, variation),
    )
    tr = (
        width + random.uniform(-variation, variation),
        0 + random.uniform(-variation, variation),
    )
    br = (
        width - x_offset + random.uniform(-variation, variation),
        height + random.uniform(-variation, variation),
    )
    bl = (
        random.uniform(-variation, variation),
        height + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 3)

    lines = [
        vec.points_between(tl, tr, 32),
        vec.points_between(tr, br, 32),
        vec.points_between(br, bl, 32),
        vec.points_between(bl, tl, 32),
    ]
    lines = lines[rm:] + lines[0:rm]

    points = [*lines[0], *lines[1], *lines[2], *lines[3], *lines[0]]

    return perfect_freehand.get_stroke_points(
        points, size=stroke_width, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_rhombus(ctx: cairo.Context[CairoSomeSurface], id: str, shape: Rhombus) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = rhombus_stroke_points(id, shape)

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


def dash_rhombus(ctx: cairo.Context[CairoSomeSurface], shape: Rhombus) -> None:
    style = shape.style
    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    # Internal angle between adjacent sides varies with width and height
    x_offset = min(width * 0.38, height * 0.38)
    points = [
        Position(x_offset, 0),
        Position(width, 0),
        Position(width - x_offset, height),
        Position(0, height),
        Position(x_offset, 0),
    ]
    finalize_geo_path(ctx, points, style)


def finalize_rhombus(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: Rhombus
) -> None:
    print(f"\tTldraw: Finalizing Rhombus: {id}")

    style = shape.style

    ctx.rotate(shape.rotation)

    if style.dash is DashStyle.DRAW:
        draw_rhombus(ctx, id, shape)
    else:
        dash_rhombus(ctx, shape)

    finalize_v2_label(ctx, shape)
