# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Adapted from: https://github.com/tldraw/tldraw/blob/main/packages/tldraw/src/lib/shapes/geo/cloudOutline.ts

from __future__ import annotations

import math
from math import atan2, tau
from random import Random
from typing import Any, Callable, List, Optional, Tuple, TypedDict, TypeVar, Union

import attr
import cairo

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import Cloud
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    DashStyle,
    SizeStyle,
    apply_geo_fill,
    circle_from_three_points,
    get_perfect_dash_props,
    get_point_on_circle,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(auto_attribs=True, slots=True)
class StraightPillSection:
    start: Position
    delta: Position
    type: str = "straight"
    center: Position = Position(-1, -1)
    start_angle: float = 0


@attr.s(auto_attribs=True, slots=True)
class ArcPillSection:
    start_angle: float
    center: Position
    type: str = "arc"
    start: Position = Position(-1, -1)
    delta: Position = Position(-1, -1)


class Arc(TypedDict):
    leftPoint: Position
    rightPoint: Position
    arcPoint: Position
    center: Optional[Position]
    radius: float


def get_pill_circumference(w: float, h: float) -> float:
    radius = min(w, h) / 2
    long_side = max(w, h) - tau
    return tau * radius + 2 * long_side


def get_pill_points(width: float, height: float, numPoints: int) -> List[Position]:
    radius = min(width, height) / 2
    long_side = max(width, height) - radius * 2
    circumference = tau * radius + 2 * long_side
    spacing = circumference / numPoints

    sections: List[Union[StraightPillSection, ArcPillSection]] = []

    if width > height:
        # Definitions for a horizontally oriented pill
        sections = [
            StraightPillSection(start=Position(radius, 0), delta=Position(1, 0)),
            ArcPillSection(
                center=Position(width - radius, radius), start_angle=-tau / 4
            ),
            StraightPillSection(
                start=Position(width - radius, height), delta=Position(-1, 0)
            ),
            ArcPillSection(center=Position(radius, radius), start_angle=tau / 4),
        ]
    else:
        # Definitions for a vertically oriented pill
        sections = [
            StraightPillSection(start=Position(width, radius), delta=Position(0, 1)),
            ArcPillSection(center=Position(radius, height - radius), start_angle=0),
            StraightPillSection(
                start=Position(0, height - radius), delta=Position(0, -1)
            ),
            ArcPillSection(center=Position(radius, radius), start_angle=tau / 2),
        ]

    points: List[Position] = []
    section_offset = 0.0

    for _ in range(numPoints):
        section = sections[0]

        if section.type == "straight":
            straight_point = vec.add(
                section.start, vec.mul(section.delta, section_offset)
            )
            points.append(Position(straight_point[0], straight_point[1]))
        else:
            point = get_point_on_circle(
                section.center, radius, section.start_angle + section_offset / radius
            )
            points.append(point)

        section_offset += spacing
        section_length = long_side if section.type == "straight" else tau / 2 * radius

        while section_offset > section_length:
            section_offset -= section_length
            sections.append(sections.pop(0))
            section = sections[0]
            section_length = (
                long_side if section.type == "straight" else tau / 2 * radius
            )

    return points


def switchSize(size: SizeStyle) -> float:
    if size is SizeStyle.S:
        return 50.0
    elif size is SizeStyle.M:
        return 70.0
    elif size is SizeStyle.L:
        return 100.0
    elif size is SizeStyle.XL:
        return 130.0
    else:
        return 70.0


def get_cloud_arcs(
    width: float, height: float, seed: str, size: SizeStyle
) -> List[Arc]:
    random = Random(seed)
    pillCircumference = get_pill_circumference(width, height)

    numBumps = max(
        math.ceil(pillCircumference / switchSize(size)),
        6,
        math.ceil(pillCircumference / min(width, height)),
    )

    targetBumpProtrusion = (pillCircumference / numBumps) * 0.2
    innerWidth = max(width - targetBumpProtrusion * 2, 1)
    innerHeight = max(height - targetBumpProtrusion * 2, 1)
    paddingX = (width - innerWidth) / 2
    paddingY = (height - innerHeight) / 2

    distanceBetweenPointsOnPerimeter = (
        get_pill_circumference(innerWidth, innerHeight) / numBumps
    )

    bumpPoints = [
        vec.add(p, (paddingX, paddingY))
        for p in get_pill_points(innerWidth, innerHeight, numBumps)
    ]
    maxWiggleX = 0 if width < 20 else targetBumpProtrusion * 0.3
    maxWiggleY = 0 if height < 20 else targetBumpProtrusion * 0.3

    for i in range(math.floor(numBumps / 2)):
        bumpPoints[i] = vec.add(
            bumpPoints[i], (random.random() * maxWiggleX, random.random() * maxWiggleY)
        )
        bumpPoints[numBumps - i - 1] = vec.add(
            bumpPoints[numBumps - i - 1],
            (random.random() * maxWiggleX, random.random() * maxWiggleY),
        )

    arcs = []

    for i in range(len(bumpPoints)):
        j = 0 if i == len(bumpPoints) - 1 else i + 1
        leftWigglePoint = bumpPoints[i]
        rightWigglePoint = bumpPoints[j]
        leftPoint = bumpPoints[i]
        rightPoint = bumpPoints[j]

        midPoint = vec.med(leftPoint, rightPoint)
        offsetAngle = vec.angle(leftPoint, rightPoint) - tau / 4

        distanceBetweenOriginalPoints = vec.dist(leftPoint, rightPoint)
        curvatureOffset = (
            distanceBetweenPointsOnPerimeter - distanceBetweenOriginalPoints
        )
        distanceBetweenWigglePoints = vec.dist(leftWigglePoint, rightWigglePoint)
        relativeSize = distanceBetweenWigglePoints / distanceBetweenOriginalPoints
        finalDistance = (max(paddingX, paddingY) + curvatureOffset) * relativeSize

        arcPoint = vec.add(midPoint, vec.from_angle(offsetAngle, finalDistance))

        arcPoint_x = (
            0 if arcPoint[0] < 0 else (width if arcPoint[0] > width else arcPoint[0])
        )
        arcPoint_y = (
            0 if arcPoint[1] < 0 else (height if arcPoint[1] > height else arcPoint[1])
        )
        arcPoint = (arcPoint_x, arcPoint_y)

        center_pos, _ = circle_from_three_points(
            leftWigglePoint, rightWigglePoint, arcPoint
        )
        center = (center_pos[0], center_pos[1])

        radius = vec.dist(
            center if center_pos else vec.med(leftWigglePoint, rightWigglePoint),
            leftWigglePoint,
        )

        arc_dict = Arc(
            leftPoint=Position(*leftWigglePoint),
            rightPoint=Position(*rightWigglePoint),
            arcPoint=Position(*arcPoint),
            center=Position(*center) if center is not None else None,
            radius=radius,
        )

        arcs.append(arc_dict)

    return arcs


def clockwise_angle_dist(a0: float, a1: float) -> float:
    a0 = a0 % tau
    a1 = a1 % tau

    if a0 > a1:
        a1 += tau

    return a1 - a0


def points_on_arc(
    start_point: Position,
    end_point: Position,
    center: Position,
    radius: float,
    num_points: int,
) -> List[Position]:
    if center is None:
        return [start_point, end_point]

    results = []

    start_angle = vec.angle(center, start_point)
    end_angle = vec.angle(center, end_point)

    l = clockwise_angle_dist(start_angle, end_angle)

    for i in range(num_points):
        t = i / (num_points - 1)
        angle = start_angle + l * t
        point = get_point_on_circle(center, radius, angle)
        results.append(point)

    return results


def mutate_point(p: Position, mut_func: Callable[[Any], Any]) -> Position:
    return Position(mut_func(p[0]), mut_func(p[1]))


def calculate_angle(center: Position, point: Position) -> float:
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    angle = atan2(dy, dx)
    return angle


def dash_cloud(ctx: cairo.Context[CairoSomeSurface], shape: Cloud, id: str) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    stroke_width = STROKE_WIDTHS[style.size]
    sw = 1 + stroke_width * 1.618

    stroke = STROKES[style.color]

    ctx.save()

    arcs: List[Arc] = get_cloud_arcs(w, h, id, style.size)

    ctx.new_sub_path()

    for arc in arcs:
        leftPoint, rightPoint, radius, center = (
            arc["leftPoint"],
            arc["rightPoint"],
            arc["radius"],
            arc["center"],
        )

        if center is None:
            # Move to leftPoint and draw a line to rightPoint instead of an arc
            ctx.move_to(*leftPoint)
            ctx.line_to(*rightPoint)
        else:
            # Calculate start and end angles
            start_angle = calculate_angle(center, leftPoint)
            end_angle = calculate_angle(center, rightPoint)

            ctx.arc(center[0], center[1], radius, start_angle, end_angle)

    ctx.close_path()

    if style.isFilled:
        preserve_path = True
        apply_geo_fill(ctx, style, preserve_path)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)

    dash_array, dash_offset = get_perfect_dash_props(
        abs(2 * w + 2 * h), sw, style.dash, snap=2, outset=False
    )

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)

    ctx.stroke()
    ctx.restore()


def draw_cloud(ctx: cairo.Context[CairoSomeSurface], shape: Cloud, id: str) -> None:
    style = shape.style
    random = Random(id)

    stroke_width = STROKE_WIDTHS[shape.style.size]
    sw = 1 + stroke_width * 1.618

    stroke = STROKES[shape.style.color]
    ctx.save()

    size_multipliers = {
        SizeStyle.S: 0.5,
        SizeStyle.M: 0.7,
        SizeStyle.L: 0.9,
        SizeStyle.XL: 1.6,
    }
    mut_multiplier = size_multipliers.get(shape.style.size, 1.0)
    mut = lambda n: n + random.random() * mut_multiplier * 2

    width = max(0, shape.size.width)
    height = max(0, shape.size.height)
    arcs = get_cloud_arcs(width, height, id, shape.style.size)
    avg_arc_length = sum(
        math.sqrt(
            (arc["leftPoint"][0] - arc["rightPoint"][0]) ** 2
            + (arc["leftPoint"][1] - arc["rightPoint"][1]) ** 2
        )
        for arc in arcs
    ) / len(arcs)
    should_mutate_points = avg_arc_length > mut_multiplier * 15

    ctx.new_sub_path()

    for arc in arcs:
        leftPoint, rightPoint, radius, center = (
            arc["leftPoint"],
            arc["rightPoint"],
            arc["radius"],
            arc["center"],
        )

        if should_mutate_points:
            leftPoint = mutate_point(leftPoint, mut)
            rightPoint = mutate_point(rightPoint, mut)

        if center is None:
            ctx.move_to(*leftPoint)
            ctx.line_to(*rightPoint)
        else:
            start_angle = calculate_angle(center, leftPoint)
            end_angle = calculate_angle(center, rightPoint)

            if should_mutate_points:
                center = mutate_point(center, mut)
                radius += random.random() * mut_multiplier

            ctx.arc(center[0], center[1], radius, start_angle, end_angle)

    ctx.close_path()

    if style.isFilled:
        preserve_path = True
        apply_geo_fill(ctx, style, preserve_path)

    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)

    dash_array, dash_offset = get_perfect_dash_props(
        abs(2 * width + 2 * height), sw, shape.style.dash, snap=2, outset=False
    )

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, shape.style.opacity)
    ctx.stroke()
    ctx.restore()


def finalize_cloud(ctx: cairo.Context[CairoSomeSurface], id: str, shape: Cloud) -> None:
    print(f"\tTldraw: Finalizing Cloud: {id}")

    ctx.rotate(shape.rotation)

    if shape.style.dash is DashStyle.DRAW:
        draw_cloud(ctx, shape, id)
    else:
        dash_cloud(ctx, shape, id)

    finalize_v2_label(ctx, shape)
