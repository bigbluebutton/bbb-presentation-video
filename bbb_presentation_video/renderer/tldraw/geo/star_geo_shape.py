# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import cos, sin, tau
from typing import List, TypeVar

import cairo
import perfect_freehand
from perfect_freehand.types import StrokePoint

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw.shape import StarGeoShape
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
)


def get_star_points(w: float, h: float, n: int) -> List[Position]:
    sides = n
    step = tau / sides / 2

    # Calculate the bounding box adjustments
    cx, cy = w / 2, h / 2
    ratio = 1
    ox, oy = (w / 2, h / 2)
    ix, iy = (ox * ratio) / 2, (oy * ratio) / 2

    points = [
        Position(
            cx + (ix if i % 2 else ox) * cos(-(tau / 4) + i * step),
            cy + (iy if i % 2 else oy) * sin(-(tau / 4) + i * step),
        )
        for i in range(sides * 2)
    ]

    return points


def star_stroke_points(id: str, shape: StarGeoShape) -> List[StrokePoint]:
    size = shape.size

    width = size.width
    height = size.height

    stroke_width = STROKE_WIDTHS[shape.style.size]

    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    vertices = 5

    star_points = get_star_points(width, height, vertices)
    strokes = []

    for i in range(len(star_points)):
        pos1 = star_points[i]
        pos2 = star_points[(i + 1) % len(star_points)]
        distance = ((pos2.x - pos1.x) ** 2 + (pos2.y - pos1.y) ** 2) ** 0.5
        strokes.append((pos1, pos2, distance))

    points = get_polygon_draw_vertices(strokes, stroke_width, id)

    return perfect_freehand.get_stroke_points(
        points, size=stroke_width, streamline=0.3, last=True
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_star(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: StarGeoShape
) -> None:
    style = shape.style

    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = star_stroke_points(id, shape)

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


def dash_star(ctx: cairo.Context[CairoSomeSurface], shape: StarGeoShape) -> None:
    style = shape.style
    width = max(0, shape.size.width)
    height = max(0, shape.size.height)

    vertices = 5
    points = get_star_points(width, height, vertices)

    finalize_geo_path(ctx, points, style)


def finalize_star(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: StarGeoShape
) -> None:
    print(f"\tTldraw: Finalizing Star: {id}")

    style = shape.style

    ctx.rotate(shape.rotation)

    if style.dash is DashStyle.DRAW:
        draw_star(ctx, id, shape)
    else:
        dash_star(ctx, shape)

    finalize_v2_label(ctx, shape)
