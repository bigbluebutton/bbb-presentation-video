# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from typing import TypeVar

import cairo
import perfect_freehand
from bbb_presentation_video.events.helpers import Position

from bbb_presentation_video.renderer.tldraw.shape import (
    XBox,
)
from bbb_presentation_video.renderer.tldraw.geo.rectangle import (
    rectangle_stroke_points,
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

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def overlay_x_cross(ctx: cairo.Context[CairoSomeSurface], shape: XBox) -> None:
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    # The cross doesn't touch the vertices of the box to
    # prevent opacities from adding up
    x_offset = 2 * sw
    y_offset = 2 * sw

    tl = (x_offset, y_offset)
    tr = (w - x_offset, y_offset)

    br = (w - x_offset, h - y_offset)
    bl = (x_offset, h - y_offset)

    ctx.move_to(*tl)
    ctx.line_to(*br)
    ctx.move_to(*tr)
    ctx.line_to(*bl)
    ctx.set_line_width(2 * sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.stroke()


def draw_x_box(ctx: cairo.Context[CairoSomeSurface], id: str, shape: XBox) -> None:
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

    overlay_x_cross(ctx, shape)


def dash_x_box(ctx: cairo.Context[CairoSomeSurface], shape: XBox) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    points = [
        Position(0, 0),
        Position(w, 0),
        Position(w, h),
        Position(0, h),
    ]

    finalize_geo_path(ctx, points, style)
    overlay_x_cross(ctx, shape)


def finalize_x_box(ctx: cairo.Context[CairoSomeSurface], id: str, shape: XBox) -> None:
    print(f"\tTldraw: Finalizing x-box: {id}")

    ctx.rotate(shape.rotation)

    if shape.style.dash is DashStyle.DRAW:
        draw_x_box(ctx, id, shape)
    else:
        dash_x_box(ctx, shape)

    finalize_v2_label(ctx, shape)
