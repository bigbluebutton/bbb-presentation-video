# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from enum import Enum
from math import floor
from random import Random
from typing import Callable, List, Optional, Sequence, TypeVar

import cairo
from perfect_freehand import get_stroke

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.easings import ease_out_quad
from bbb_presentation_video.renderer.tldraw.shape import LineShape, apply_shape_rotation
from bbb_presentation_video.renderer.tldraw.shape.text import finalize_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    SplineType,
    Style,
    bezier_length,
    draw_smooth_path,
    get_perfect_dash_props,
    lerp_angles,
    rounded_rect,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def freehand_line_shaft(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    style: Style,
    start: Position,
    end: Position,
) -> None:
    random = Random(id)
    stroke_width = STROKE_WIDTHS[style.size]

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


def curved_freehand_line_shaft(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    style: Style,
    start: Position,
    end: Position,
    center: Position,
    radius: float,
    length: float,
    easing: Callable[[float], float],
) -> None:

    random = Random(id)
    stroke_width = STROKE_WIDTHS[style.size]
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


def straight_line(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: LineShape
) -> float:
    style = shape.style
    start = shape.handles.start
    end = shape.handles.end

    line_dist = vec.dist(start, end)
    if line_dist < 2:
        return line_dist

    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618

    stroke = STROKES[style.color]

    # Path between start and end points
    ctx.save()
    if style.dash is DashStyle.DRAW:
        freehand_line_shaft(ctx, id, style, start, end)

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
            line_dist, stroke_width * 1.618, style.dash, snap=2, outset=False
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
        ctx.stroke()
    ctx.restore()

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    ctx.stroke()

    return line_dist


def bent_line(ctx: cairo.Context[CairoSomeSurface], id: str, shape: LineShape) -> float:
    style = shape.style
    start = shape.handles.start
    controlPoint = shape.handles.controlPoint
    end = shape.handles.end

    # Calculate distances
    line_dist_start_control = vec.dist(start, controlPoint)
    line_dist_control_end = vec.dist(controlPoint, end)

    # Early return if both lines are too short
    if line_dist_start_control < 2 and line_dist_control_end < 2:
        return line_dist_start_control + line_dist_control_end

    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618
    stroke = STROKES[style.color]

    ctx.save()
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)

    if style.dash is DashStyle.DRAW:
        freehand_line_shaft(ctx, id, style, start, controlPoint)
        freehand_line_shaft(ctx, id, style, controlPoint, end)

        ctx.fill_preserve()
        ctx.stroke()

    else:
        if style.dash is DashStyle.DOTTED:
            ctx.set_dash([0, stroke_width * 4])
        elif style.dash is DashStyle.DASHED:
            ctx.set_dash([stroke_width * 4, stroke_width * 4])

        # Draw first segment: start to control point
        ctx.move_to(start.x, start.y)
        ctx.line_to(controlPoint.x, controlPoint.y)
        ctx.stroke()

        # Draw second segment: control point to end
        ctx.move_to(controlPoint.x, controlPoint.y)
        ctx.line_to(end.x, end.y)
        ctx.stroke()

    ctx.restore()

    return line_dist_start_control + line_dist_control_end


def curved_line(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: LineShape
) -> float:
    style = shape.style
    start = shape.handles.start
    controlPoint = shape.handles.controlPoint
    end = shape.handles.end

    line_dist = vec.dist(start, end)

    if line_dist < 2:
        return line_dist

    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618

    # Calculate a path passing through the control point
    # t is fixed at 0.5 for the midpoint
    t = 0.5

    # Compute adjusted control points
    b_x = (controlPoint.x - (1 - t) ** 3 * start.x - t**3 * end.x) / (3 * (1 - t) * t)
    b_y = (controlPoint.y - (1 - t) ** 3 * start.y - t**3 * end.y) / (3 * (1 - t) * t)
    c_x = b_x
    c_y = b_y

    # Move to the start position
    ctx.move_to(start.x, start.y)

    # Draw cubic Bézier curve
    ctx.curve_to(b_x, b_y, c_x, c_y, end.x, end.y)

    # Get the length of the curve
    length = bezier_length(start, controlPoint, end)
    stroke = STROKES[style.color]

    ctx.save()

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

    return abs(length)


def finalize_line(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: LineShape
) -> None:
    print(f"\tTldraw: Finalizing Line: {id}")

    apply_shape_rotation(ctx, shape)

    ctx.push_group()

    if shape.spline == SplineType.CUBIC:
        curved_line(ctx, id, shape)
    elif shape.spline == SplineType.LINE:
        bent_line(ctx, id, shape)
    else:
        straight_line(ctx, id, shape)

    line_pattern = ctx.pop_group()

    ctx.set_source(line_pattern)
    ctx.paint()
