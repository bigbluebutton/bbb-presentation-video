# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import floor, pi, tau
from random import Random
from typing import Callable, List, Optional, Sequence, TypeVar

import cairo
from perfect_freehand import get_stroke

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.easings import (
    ease_in_out_cubic,
    ease_in_out_sine,
    ease_out_quad,
)
from bbb_presentation_video.renderer.tldraw.intersect import (
    intersect_circle_circle,
    intersect_circle_line_segment,
)
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.shape.text import finalize_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    Decoration,
    Style,
    circle_from_three_points,
    draw_smooth_path,
    get_perfect_dash_props,
    get_sweep,
    lerp_angles,
    rounded_rect,
)


def get_arc_length(C: Position, r: float, A: Position, B: Position) -> float:
    sweep = get_sweep(C, A, B)
    return r * tau * (sweep / tau)


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def freehand_arrow_shaft(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    style: Style,
    start: Position,
    end: Position,
    deco_start: Optional[Decoration],
    deco_end: Optional[Decoration],
) -> None:
    random = Random(id)
    stroke_width = STROKE_WIDTHS[style.size]
    if deco_start is not None:
        start = Position(vec.nudge(start, end, stroke_width))
    if deco_end is not None:
        end = Position(vec.nudge(end, start, stroke_width))

    stroke_outline_points = get_stroke(
        [start, end],
        size=stroke_width,
        thinning=0.618 + random.uniform(-0.2, 0.2),
        easing=ease_out_quad,
        simulate_pressure=True,
        streamline=0,
        last=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)


def curved_freehand_arrow_shaft(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    style: Style,
    start: Position,
    end: Position,
    deco_start: Optional[Decoration],
    deco_end: Optional[Decoration],
    center: Position,
    radius: float,
    length: float,
    easing: Callable[[float], float],
) -> None:
    random = Random(id)
    stroke_width = STROKE_WIDTHS[style.size]
    if deco_start is not None:
        start = Position(vec.rot_with(start, center, stroke_width / length))
    if deco_end is not None:
        end = Position(vec.rot_with(end, center, -(stroke_width / length)))
    start_angle = vec.angle(center, start)
    end_angle = vec.angle(center, end)

    points: List[Sequence[float]] = [start]
    count = 8 + floor((abs(length) / 20) * 1 + random.uniform(-0.5, 0.5))
    for i in range(count):
        t = easing(i / count)
        angle = lerp_angles(start_angle, end_angle, t)
        points.append(vec.to_fixed(vec.nudge_at_angle(center, angle, radius)))
    points.append(end)

    stroke_outline_points = get_stroke(
        points,
        size=1 + stroke_width,
        thinning=0.618 + random.uniform(-0.2, 0.2),
        easing=ease_out_quad,
        simulate_pressure=False,
        streamline=0,
        last=True,
    )
    draw_smooth_path(ctx, stroke_outline_points, closed=True)


def curved_arrow_shaft(
    ctx: cairo.Context[CairoSomeSurface],
    start: Position,
    end: Position,
    center: Position,
    radius: float,
    bend: float,
) -> None:
    start_angle = vec.angle(center, start)
    end_angle = vec.angle(center, end)

    ctx.new_sub_path()

    if bend > 0:
        ctx.arc(center.x, center.y, radius, start_angle, end_angle)
    else:
        ctx.arc_negative(center.x, center.y, radius, start_angle, end_angle)


def straight_arrow_head(
    ctx: cairo.Context[CairoSomeSurface],
    a: Position,
    b: Position,
    r: float,
) -> None:
    ints = intersect_circle_line_segment(a, r, a, b).points
    if len(ints) == 0:
        print("\t\tCould not find an intersection for the arrow head.")
        left = a
        right = a
    else:
        int = ints[0]
        left = Position(vec.rot_with(int, a, pi / 6))
        right = Position(vec.rot_with(int, a, -pi / 6))

    ctx.move_to(left.x, left.y)
    ctx.line_to(a.x, a.y)
    ctx.line_to(right.x, right.y)


def curved_arrow_head(
    ctx: cairo.Context[CairoSomeSurface],
    a: Position,
    r1: float,
    C: Position,
    r2: float,
    sweep: bool,
) -> None:
    ints = intersect_circle_circle(a, r1 * 0.618, C, r2).points
    if len(ints) == 0:
        print("\t\tCould not find an intersection for the arrow head.")
        left = a
        right = a
    else:
        int = ints[0] if sweep else ints[1]
        left = Position(vec.nudge(vec.rot_with(int, a, pi / 6), a, r1 * -0.382))
        right = Position(vec.nudge(vec.rot_with(int, a, -pi / 6), a, r1 * -0.382))

    ctx.move_to(left.x, left.y)
    ctx.line_to(a.x, a.y)
    ctx.line_to(right.x, right.y)


def straight_arrow(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: ArrowShape
) -> float:
    style = shape.style
    start = shape.handles.start
    end = shape.handles.end
    deco_start = shape.decorations.start
    deco_end = shape.decorations.end

    arrow_dist = vec.dist(start, end)
    if arrow_dist < 2:
        return arrow_dist
    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618

    stroke = STROKES[style.color]

    # Path between start and end points
    ctx.save()
    if style.dash is DashStyle.DRAW:
        freehand_arrow_shaft(ctx, id, style, start, end, deco_start, deco_end)

        ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
        ctx.fill_preserve()
        ctx.set_line_width(sw / 2)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.stroke()
    else:
        ctx.move_to(start[0], start[1])
        ctx.line_to(end[0], end[1])

        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        dash_array, dash_offset = get_perfect_dash_props(
            arrow_dist, stroke_width * 1.618, style.dash, snap=2, outset=False
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
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
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.stroke()

    return arrow_dist


def curved_arrow(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: ArrowShape
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
    random = Random(id)
    easing = random.choice([ease_in_out_sine, ease_in_out_cubic])

    stroke = STROKES[style.color]

    ctx.save()
    if style.dash is DashStyle.DRAW:
        curved_freehand_arrow_shaft(
            ctx,
            id,
            style,
            start,
            end,
            deco_start,
            deco_end,
            center,
            radius,
            length,
            easing,
        )

        ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
        ctx.fill()
    else:
        curved_arrow_shaft(ctx, start, end, center, radius, arrow_bend)

        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        dash_array, dash_offset = get_perfect_dash_props(
            abs(length), sw, style.dash, snap=2, outset=False
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
        ctx.stroke()
    ctx.restore()

    # Arrowheads
    arrow_head_len = min(arrow_dist / 3, stroke_width * 8)
    if deco_start is Decoration.ARROW:
        curved_arrow_head(ctx, start, arrow_head_len, center, radius, length < 0)
    if deco_end is Decoration.ARROW:
        curved_arrow_head(ctx, end, arrow_head_len, center, radius, length >= 0)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.stroke()

    return abs(length)


def finalize_arrow(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: ArrowShape
) -> None:
    print(f"\tTldraw: Finalizing Arrow: {id}")

    apply_shape_rotation(ctx, shape)

    start = shape.handles.start
    bend = shape.handles.bend
    end = shape.handles.end
    is_straight_line = vec.dist(bend, vec.to_fixed(vec.med(start, end))) < 1

    ctx.push_group()
    if is_straight_line:
        dist = straight_arrow(ctx, id, shape)
    else:
        dist = curved_arrow(ctx, id, shape)
    arrow_pattern = ctx.pop_group()

    label = shape.label
    if label is not None:
        bounds = shape.size
        offset = Position(bend.x - bounds.width / 2, bend.y - bounds.height / 2)
        label_size, scale_adj = finalize_label(
            ctx,
            shape,
            offset=offset,
            scale=lambda ls: max(
                0.5,
                min(1, max(dist / (ls.width + 128), dist / (ls.height + 128))),
            ),
        )

        # Mask the label area so the arrow doesn't overlap it
        ctx.push_group_with_content(cairo.Content.ALPHA)
        ctx.rectangle(-100, -100, bounds.width + 200, bounds.height + 200)
        ctx.fill()
        ctx.set_operator(cairo.Operator.DEST_OUT)
        ctx.translate(
            bounds.width / 2 - label_size.width / 2 + offset.x,
            bounds.height / 2 - label_size.height / 2 + offset.y,
        )
        rounded_rect(ctx, label_size, 4 * scale_adj)
        ctx.fill()
        mask = ctx.pop_group()

        ctx.set_source(arrow_pattern)
        ctx.mask(mask)
    else:
        ctx.set_source(arrow_pattern)
        ctx.paint()
