# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import floor
from random import Random
from typing import List, Tuple, TypeVar

import cairo
import perfect_freehand

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import ArrowGeo
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    GeoShape,
    apply_geo_fill,
    draw_smooth_path,
    draw_smooth_stroke_point_path,
    finalize_geo_path,
)


def arrow_geo_stroke_points(
    id: str, shape: ArrowGeo
) -> List[perfect_freehand.types.StrokePoint]:
    random = Random(id)
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    variation = sw * 0.75

    v = []

    if shape.geo is GeoShape.ARROW_DOWN:
        oy = min(w, h) * 0.38
        ox = w * 0.16
        v = [
            (
                ox + random.uniform(-variation, variation),
                random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                w + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                w / 2 + random.uniform(-variation, variation),
                h + random.uniform(-variation, variation),
            ),
            (
                random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
        ]
    elif shape.geo is GeoShape.ARROW_LEFT:
        ox = min(w, h) * 0.38
        oy = h * 0.16
        v = [
            (
                ox + random.uniform(-variation, variation),
                random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                h + random.uniform(-variation, variation),
            ),
            (
                random.uniform(-variation, variation),
                h / 2 + random.uniform(-variation, variation),
            ),
        ]
    elif shape.geo is GeoShape.ARROW_UP:
        oy = min(w, h) * 0.38
        ox = w * 0.16
        v = [
            (
                w / 2 + random.uniform(-variation, variation),
                random.uniform(-variation, variation),
            ),
            (
                w + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                h + random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                h + random.uniform(-variation, variation),
            ),
            (
                ox + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
        ]
    else:
        ox = min(w, h) * 0.38
        oy = h * 0.16
        v = [
            (
                random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                oy + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                random.uniform(-variation, variation),
            ),
            (
                w + random.uniform(-variation, variation),
                h / 2 + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                h + random.uniform(-variation, variation),
            ),
            (
                w - ox + random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
            (
                random.uniform(-variation, variation),
                h - oy + random.uniform(-variation, variation),
            ),
        ]
    # Which side to start drawing first
    rm = random.randrange(0, 4)

    # Number of points per side
    p = max(8, floor(w / 16))

    lines = [vec.points_between(v[i], v[(i + 1) % len(v)], p) for i in range(len(v))]

    lines = lines[rm:] + lines[0:rm]

    points: List[Tuple[float, float, float]] = [
        *lines[0],
        *lines[1],
        *lines[2],
        *lines[3],
        *lines[4],
        *lines[5],
        *lines[6],
        *lines[0],
    ]

    return perfect_freehand.get_stroke_points(
        points[5 : floor(len(lines[0]) / -2) + 3],
        size=sw,
        streamline=0.3,
        last=True,
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_geo_arrow(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: ArrowGeo
) -> None:
    style = shape.style
    is_filled = style.isFilled
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = arrow_geo_stroke_points(id, shape)

    if is_filled:
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


def dash_geo_arrow(ctx: cairo.Context[CairoSomeSurface], shape: ArrowGeo) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    if shape.geo == GeoShape.ARROW_DOWN or shape.geo == GeoShape.ARROW_UP:
        ox = w * 0.16
        oy = min(w, h) * 0.38
    else:
        ox = min(w, h) * 0.38
        oy = h * 0.16

    if shape.geo == GeoShape.ARROW_UP:
        points = [
            Position(w / 2, 0),
            Position(w, oy),
            Position(w - ox, oy),
            Position(w - ox, h),
            Position(ox, h),
            Position(ox, oy),
            Position(0, oy),
        ]
    elif shape.geo == GeoShape.ARROW_DOWN:
        points = [
            Position(ox, 0),
            Position(w - ox, 0),
            Position(w - ox, h - oy),
            Position(w, h - oy),
            Position(w / 2, h),
            Position(0, h - oy),
            Position(ox, h - oy),
        ]
    elif shape.geo == GeoShape.ARROW_LEFT:
        points = [
            Position(ox, 0),
            Position(ox, oy),
            Position(w, oy),
            Position(w, h - oy),
            Position(ox, h - oy),
            Position(ox, h),
            Position(0, h / 2),
        ]
    else:
        points = [
            Position(0, oy),
            Position(w - ox, oy),
            Position(w - ox, 0),
            Position(w, h / 2),
            Position(w - ox, h),
            Position(w - ox, h - oy),
            Position(0, h - oy),
        ]

    finalize_geo_path(ctx, points, style)


def finalize_geo_arrow(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: ArrowGeo
) -> None:
    print(f"\tTldraw: Finalizing Arrow (geo): {id}")

    ctx.rotate(shape.rotation)

    if shape.style.dash is DashStyle.DRAW:
        draw_geo_arrow(ctx, id, shape)
    else:
        dash_geo_arrow(ctx, shape)

    finalize_v2_label(ctx, shape)
