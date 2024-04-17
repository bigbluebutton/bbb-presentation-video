# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import floor
from random import Random
from typing import List, Tuple, TypeVar, Union

import cairo
import perfect_freehand

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    CheckBoxGeoShape,
    RectangleGeoShape,
    XBoxGeoShape,
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


def rectangle_stroke_points(
    id: str, shape: Union[RectangleGeoShape, XBoxGeoShape, CheckBoxGeoShape]
) -> List[perfect_freehand.types.StrokePoint]:
    random = Random(id)
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    # Corners
    variation = sw * 0.75
    tl = (
        sw / 2 + random.uniform(-variation, variation),
        sw / 2 + random.uniform(-variation, variation),
    )
    tr = (
        w - sw / 2 + random.uniform(-variation, variation),
        sw / 2 + random.uniform(-variation, variation),
    )
    br = (
        w - sw / 2 + random.uniform(-variation, variation),
        h - sw / 2 + random.uniform(-variation, variation),
    )
    bl = (
        sw / 2 + random.uniform(-variation, variation),
        h - sw / 2 + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 4)

    # Corner radii
    rx = min(w / 4, sw * 2)
    ry = min(h / 4, sw / 2)

    # Number of points per side
    px = max(8, floor(w / 16))
    py = max(8, floor(h / 16))

    # Inset each line by the corner radii and let the freehand algo
    # interpolate points for the corners.
    lines = [
        vec.points_between(vec.add(tl, (rx, 0)), vec.sub(tr, (rx, 0)), px),
        vec.points_between(vec.add(tr, (0, ry)), vec.sub(br, (0, ry)), py),
        vec.points_between(vec.sub(br, (rx, 0)), vec.add(bl, (rx, 0)), px),
        vec.points_between(vec.sub(bl, (0, ry)), vec.add(tl, (0, ry)), py),
    ]
    lines = lines[rm:] + lines[0:rm]

    # For the final points, include the first half of the first line again,
    # so that the line wraps around and avoids ending on a sharp corner.
    # This has a bit of finesse and magic—if you change the points_between
    # function, then you'll likely need to change this one too.
    points: List[Tuple[float, float, float]] = [
        *lines[0],
        *lines[1],
        *lines[2],
        *lines[3],
        *lines[0],
    ]

    return perfect_freehand.get_stroke_points(
        points[5 : floor(len(lines[0]) / -2) + 3],
        size=sw,
        streamline=0.3,
        last=True,
    )


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def draw_rectangle(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: RectangleGeoShape
) -> None:
    style = shape.style
    is_filled = style.isFilled
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    stroke_points = rectangle_stroke_points(id, shape)

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


def dash_rectangle(ctx: cairo.Context[CairoSomeSurface], shape: RectangleGeoShape) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    points = [Position(0, 0), Position(w, 0), Position(w, h), Position(0, h)]

    finalize_geo_path(ctx, points, style)


def finalize_geo_rectangle(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: RectangleGeoShape
) -> None:
    print(f"\tTldraw: Finalizing Rectangle (geo): {id}")

    ctx.rotate(shape.rotation)

    if shape.style.dash is DashStyle.DRAW:
        draw_rectangle(ctx, id, shape)
    else:
        dash_rectangle(ctx, shape)

    finalize_v2_label(ctx, shape)
