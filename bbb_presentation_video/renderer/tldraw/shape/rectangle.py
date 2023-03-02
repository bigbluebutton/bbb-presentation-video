# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import floor
from random import Random
from typing import List, Tuple, TypeVar

import cairo
import perfect_freehand

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    RectangleShape,
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


def rectangle_stroke_points(
    id: str, shape: RectangleShape
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


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def draw_rectangle(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: RectangleShape
) -> None:
    style = shape.style
    is_filled = style.isFilled
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]
    fill = FILLS[style.color]

    stroke_points = rectangle_stroke_points(id, shape)

    if is_filled:
        draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill()

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


def dash_rectangle(
    ctx: "cairo.Context[CairoSomeSurface]", shape: RectangleShape
) -> None:
    style = shape.style
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]
    fill = FILLS[style.color]

    sw = 1 + stroke_width * 1.618
    w = max(0, shape.size.width - sw / 2)
    h = max(0, shape.size.height - sw / 2)

    if style.isFilled:
        ctx.move_to(sw / 2, sw / 2)
        ctx.line_to(w, sw / 2)
        ctx.line_to(w, h)
        ctx.line_to(sw / 2, h)
        ctx.close_path()
        ctx.set_source_rgb(fill.r, fill.g, fill.b)
        ctx.fill()

    strokes = [
        ((sw / 2, sw / 2), (w, sw / 2), w - sw / 2),
        ((w, sw / 2), (w, h), h - sw / 2),
        ((w, h), (sw / 2, h), w - sw / 2),
        ((sw / 2, h), (sw / 2, sw / 2), h - sw / 2),
    ]
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    for start, end, length in strokes:
        dash_array, dash_offset = get_perfect_dash_props(
            length, stroke_width * 1.618, style.dash
        )
        ctx.move_to(start[0], start[1])
        ctx.line_to(end[0], end[1])
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()


def finalize_rectangle(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: RectangleShape
) -> None:
    print(f"\tTldraw: Finalizing Rectangle: {id}")

    apply_shape_rotation(ctx, shape)

    if shape.style.dash is DashStyle.DRAW:
        draw_rectangle(ctx, id, shape)
    else:
        dash_rectangle(ctx, shape)

    finalize_label(ctx, shape)
