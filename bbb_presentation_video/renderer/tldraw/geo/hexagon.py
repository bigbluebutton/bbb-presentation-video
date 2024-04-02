# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import List, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.renderer.tldraw.shape import Hexagon
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    apply_geo_fill,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    finalize_geo_path,
    get_polygon_draw_vertices,
    get_polygon_strokes,
)


def hexagon_stroke_points(id: str, shape: Hexagon) -> List[StrokePoint]:
    size = shape.size

    width = size.width
    height = size.height

    stroke_width = STROKE_WIDTHS[shape.style.size]

    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    sides = 6

    strokes = get_polygon_strokes(width, height, sides)
    points = get_polygon_draw_vertices(strokes, stroke_width, id)

    return perfect_freehand.get_stroke_points(
        points, size=stroke_width, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_hexagon(ctx: cairo.Context[CairoSomeSurface], id: str, shape: Hexagon) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = hexagon_stroke_points(id, shape)

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


def dash_hexagon(ctx: cairo.Context[CairoSomeSurface], shape: Hexagon) -> None:
    style = shape.style
    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    sides = 6

    strokes = get_polygon_strokes(width, height, sides)
    points = [stroke[0] for stroke in strokes]

    finalize_geo_path(ctx, points, style)


def finalize_hexagon(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: Hexagon
) -> None:
    print(f"\tTldraw: Finalizing Hexagon: {id}")

    style = shape.style

    ctx.rotate(shape.rotation)

    if style.dash is DashStyle.DRAW:
        draw_hexagon(ctx, id, shape)
    else:
        dash_hexagon(ctx, shape)

    finalize_v2_label(ctx, shape)
