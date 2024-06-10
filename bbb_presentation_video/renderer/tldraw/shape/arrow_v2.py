# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShapeV2,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.shape.arrow import (
    curved_arrow_head,
    curved_arrow_shaft,
    straight_arrow_head,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    Decoration,
    circle_from_three_points,
    get_arc_length,
    get_perfect_dash_props,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def straight_arrow(ctx: cairo.Context[CairoSomeSurface], shape: ArrowShapeV2) -> float:
    style = shape.style
    start = shape.handles.start
    end = shape.handles.end
    deco_start = shape.decorations.start
    deco_end = shape.decorations.end
    opacity = style.opacity
    arrow_dist = vec.dist(start, end)
    if arrow_dist < 2:
        return arrow_dist
    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618

    stroke = STROKES[style.color]

    # Path between start and end points
    ctx.save()

    ctx.move_to(start[0], start[1])
    ctx.line_to(end[0], end[1])

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    dash_array, dash_offset = get_perfect_dash_props(
        arrow_dist, stroke_width * 1.618, style.dash, snap=2, outset=False
    )
    ctx.set_dash(dash_array, dash_offset)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, opacity)
    ctx.stroke()
    ctx.restore()

    # Arrowheads
    arrow_head_len = min(arrow_dist / 3, stroke_width * 8)
    if deco_start is Decoration.ARROW:
        straight_arrow_head(ctx, start, end, arrow_head_len)
    if deco_end is Decoration.ARROW:
        straight_arrow_head(ctx, end, start, arrow_head_len)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, opacity)
    ctx.stroke()

    return arrow_dist


def get_midpoint(start: Position, end: Position, bend: float) -> Position:
    mid = [(start.x + end.x) / 2, (start.y + end.y) / 2]

    unit_vector = vec.uni([end.x - start.x, end.y - start.y])

    unit_rotated = [unit_vector[1], -unit_vector[0]]
    bend_offset = [unit_rotated[0] * -bend, unit_rotated[1] * -bend]

    middle = Position(mid[0] + bend_offset[0], mid[1] + bend_offset[1])

    return middle


def curved_arrow(
    ctx: cairo.Context[CairoSomeSurface],
    shape: ArrowShapeV2,
) -> float:
    style = shape.style
    start = shape.handles.start
    bend = shape.handles.bend
    end = shape.handles.end
    arrow_bend = shape.bend
    deco_start = shape.decorations.start
    deco_end = shape.decorations.end

    arrow_dist = vec.dist(start, end)
    if arrow_dist < 2:
        return arrow_dist

    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618
    # Calculate a path as a segment of a circle passing through the three points start, bend, and end
    center, radius = circle_from_three_points(start, bend, end)
    length = get_arc_length(center, radius, start, end)
    stroke = STROKES[style.color]

    ctx.save()

    arrow_bend = -arrow_bend

    curved_arrow_shaft(ctx, start, end, center, radius, arrow_bend)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    dash_array, dash_offset = get_perfect_dash_props(
        abs(length), sw, style.dash, snap=2, outset=False
    )

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
    ctx.stroke()
    ctx.restore()

    # Arrowheads
    arrow_head_len = min(arrow_dist / 3, stroke_width * 8)

    sweepFlag = (
        (end.x - start.x) * (bend.y - start.y) - (bend.x - start.x) * (end.y - start.y)
    ) < 0

    if deco_start is not Decoration.NONE:
        curved_arrow_head(ctx, start, arrow_head_len, center, radius, sweepFlag)
    if deco_end is not Decoration.NONE:
        curved_arrow_head(ctx, end, arrow_head_len, center, radius, sweepFlag)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
    ctx.stroke()

    return abs(length)


def finalize_arrow_v2(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: ArrowShapeV2,
) -> None:
    print(f"\tTldraw: Finalizing Arrow (v2): {id}")

    apply_shape_rotation(ctx, shape)

    start = shape.handles.start
    end = shape.handles.end

    is_straight_line = shape.bend == 0.0
    shape.handles.bend = get_midpoint(start, end, shape.bend)

    ctx.push_group()
    if is_straight_line:
        straight_arrow(ctx, shape)
    else:
        curved_arrow(ctx, shape)

    arrow_pattern = ctx.pop_group()
    ctx.set_source(arrow_pattern)
    ctx.paint()
