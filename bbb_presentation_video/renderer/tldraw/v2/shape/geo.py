# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
# SPDX-FileCopyrightText: 2023 tldraw GB Ltd. <hello@tldraw.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later AND Apache-2.0

from __future__ import annotations

from enum import Enum
from itertools import chain, pairwise
from math import cos, fabs, floor, sin, tau
from random import Random
from typing import List, Protocol, Sequence, Tuple, TypeVar, runtime_checkable

import attr
import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape.proto import LabelledShapeProto
from bbb_presentation_video.renderer.tldraw.utils import (
    DashStyle,
    Style,
    bezier_quad_to_cube,
    get_perfect_dash_props,
)
from bbb_presentation_video.renderer.tldraw.v2.shape.text import finalize_label
from bbb_presentation_video.renderer.tldraw.v2.utils import (
    COLORS,
    STROKE_SIZES,
    apply_geo_fill,
    polygon_vertices,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


class GeoShape(Enum):
    ARROW_DOWN = "arrow-down"
    ARROW_LEFT = "arrow-left"
    ARROW_RIGHT = "arrow-right"
    ARROW_UP = "arrow-up"
    CHECKBOX = "check-box"
    CLOUD = "cloud"
    DIAMOND = "diamond"
    ELLIPSE = "ellipse"
    HEXAGON = "hexagon"
    OCTAGON = "octagon"
    NONE = ""
    OVAL = "oval"
    PENTAGON = "pentagon"
    RECTANGLE = "rectangle"
    RHOMBUS = "rhombus"
    RHOMBUS_2 = "rhombus-2"
    STAR = "star"
    TRAPEZOID = "trapezoid"
    TRIANGLE = "triangle"
    XBOX = "x-box"


@attr.s(order=False, slots=True, auto_attribs=True)
@runtime_checkable
class GeoShapeProto(LabelledShapeProto, Protocol):
    geo: GeoShape = GeoShape.NONE
    """Which geo type the shape is"""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            props = data["props"]

            if "geo" in props:
                self.geo = GeoShape(props["geo"])

    def get_shape_geometry(self) -> List[vec.V]:
        """Get the list of points for the outline of a polygonal geo shape"""
        return []

    def get_lines(self) -> List[Tuple[vec.V, vec.V]]:
        """Get a list of lines that will be drawn over the geo shape"""
        return []

    def finalize_shape(self, ctx: cairo.Context[CairoSomeSurface], id: str) -> None:
        """Draw the shape itself (not including label).

        Default implementation is for polygonal shapes; override this method for non-polygonal shapes."""

        outline = self.get_shape_geometry()
        lines = self.get_lines()

        style = self.style
        dash = style.dash
        if dash is DashStyle.DRAW:
            geo_draw_polygon(ctx, id, style, outline, lines)
        elif dash is DashStyle.SOLID:
            geo_solid_polygon(ctx, style, outline, lines)
        elif dash is DashStyle.DASHED or dash is DashStyle.DOTTED:
            geo_dash_polygon(ctx, style, outline, lines)

    def finalize(self, ctx: cairo.Context[CairoSomeSurface], id: str) -> None:
        print(f"\tTldraw: Finalizing Geo Shape ({self.geo}): {id}")
        ctx.push_group()

        ctx.rotate(self.rotation)

        ctx.save()
        self.finalize_shape(ctx, id)
        ctx.restore()
        finalize_label(ctx, self)

        ctx.pop_group_to_source()
        ctx.paint_with_alpha(self.style.opacity)


@attr.s(order=False, slots=True, auto_attribs=True)
class TriangleGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        cx = w / 2
        return [(cx, 0), (w, h), (0, h)]


@attr.s(order=False, slots=True, auto_attribs=True)
class DiamondGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        cx = w / 2
        cy = w / 2
        return [(cx, 0), (w, cy), (cx, h), (0, cy)]


@attr.s(order=False, slots=True, auto_attribs=True)
class RectangleGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        return [(0, 0), (w, 0), (w, h), (0, h)]


@attr.s(order=False, slots=True, auto_attribs=True)
class PentagonGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        return polygon_vertices(w, h, 5)


@attr.s(order=False, slots=True, auto_attribs=True)
class HexagonGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        return polygon_vertices(w, h, 6)


@attr.s(order=False, slots=True, auto_attribs=True)
class OctagonGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        return polygon_vertices(w, h, 8)


# TODO: EllipseGeoShape

# TODO: OvalGeoShape


@attr.s(order=False, slots=True, auto_attribs=True)
class StarGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)

        # Most of this code is to offset the center, a 5 point star
        # will need to be moved downward because from its center [0,0]
        # it will have a bigger minY than maxY. This is because it'll
        # have 2 points at the bottom.
        sides = 5
        step = tau / sides / 2
        rightmost_index = floor(sides / 4) * 2
        leftmost_index = sides * 2 - rightmost_index
        topmost_index = 0
        bottommost_index = floor(sides / 2) * 2
        max_x = cos(-tau / 4 + rightmost_index * step) * w / 2
        min_x = cos(-tau / 4 + leftmost_index * step) * w / 2

        min_y = sin(-tau / 4 + topmost_index * step) * h / 2
        max_y = sin(-tau / 4 + bottommost_index * step) * h / 2
        diff_x = w - fabs(max_x - min_x)
        diff_y = h - fabs(max_y - min_y)
        offset_x = w / 2 + min_x - (w / 2 - max_x)
        offset_y = h / 2 + min_y - (h / 2 - max_y)

        ratio = 1
        cx = (w - offset_x) / 2
        cy = (h - offset_y) / 2
        ox = (w + diff_x) / 2
        oy = (h + diff_y) / 2
        ix = (ox * ratio) / 2
        iy = (ox * ratio) / 2

        points = []
        for i in range(0, sides * 2):
            theta = -tau / 4 + i * step
            points.append(
                (
                    cx + (ix if i % 2 else ox) * cos(theta),
                    cy + (iy if i % 2 else oy) * sin(theta),
                )
            )
        return points


@attr.s(order=False, slots=True, auto_attribs=True)
class RhombusGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        offset = min(w * 0.38, h * 0.38)
        return [(offset, 0), (w, 0), (w - offset, h), (0, h)]


@attr.s(order=False, slots=True, auto_attribs=True)
class Rhombus2GeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        offset = min(w * 0.38, h * 0.38)
        return [(0, 0), (w - offset, 0), (w, h), (offset, h)]


@attr.s(order=False, slots=True, auto_attribs=True)
class TrapezoidGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        offset = min(w * 0.38, h * 0.38)
        return [(offset, 0), (w - offset, 0), (w, h), (0, h)]


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowRightGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        ox = min(w, h) * 0.38
        oy = h * 0.16
        return [
            (0, oy),
            (w - ox, oy),
            (w - ox, 0),
            (w, h / 2),
            (w - ox, h),
            (w - ox, h - oy),
            (0, h - oy),
        ]


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowLeftGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        ox = min(w, h) * 0.38
        oy = h * 0.16
        return [
            (ox, 0),
            (ox, oy),
            (w, oy),
            (w, h - oy),
            (ox, h - oy),
            (ox, h),
            (0, h / 2),
        ]


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowUpGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        ox = w * 0.16
        oy = min(w, h) * 0.38
        return [
            (w / 2, 0),
            (w, oy),
            (w - ox, oy),
            (w - ox, h),
            (ox, h),
            (ox, oy),
            (0, oy),
        ]


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowDownGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def get_shape_geometry(self) -> List[vec.V]:
        w = max(1.0, self.size.width)
        h = max(1.0, self.size.height)
        ox = w * 0.16
        oy = min(w, h) * 0.38
        return [
            (ox, 0),
            (w - ox, 0),
            (w - ox, h - oy),
            (w, h - oy),
            (w / 2, h),
            (0, h - oy),
            (ox, h - oy),
        ]


@attr.s(order=False, slots=True, auto_attribs=True)
class CheckBoxGeoShape(RectangleGeoShape):
    def get_lines(self) -> List[Tuple[vec.V, vec.V]]:
        w = self.size.width
        h = self.size.height

        size = min(w, h) * 0.82
        ox = (w - size) / 2
        oy = (h - size) / 2

        def clamp_x(x: float) -> float:
            return max(0, min(w, x))

        def clamp_y(y: float) -> float:
            return max(0, min(h, y))

        return [
            (
                (clamp_x(ox + size * 0.25), clamp_y(oy + size * 0.52)),
                (clamp_x(ox + size * 0.45), clamp_y(oy + size * 0.82)),
            ),
            (
                (clamp_x(ox + size * 0.45), clamp_y(oy + size * 0.82)),
                (clamp_x(ox + size * 0.82), clamp_y(oy + size * 0.22)),
            ),
        ]


@attr.s(order=False, slots=True, auto_attribs=True)
class XBoxGeoShape(RectangleGeoShape):
    def get_lines(self) -> List[Tuple[vec.V, vec.V]]:
        dash = self.style.dash
        w = self.size.width
        h = self.size.height

        if dash is DashStyle.DASHED:
            cw = w / 2
            ch = h / 2
            return [
                ((0, 0), (cw, ch)),
                ((w, h), (cw, ch)),
                ((0, h), (cw, ch)),
                ((w, 0), (cw, ch)),
            ]

        sw = STROKE_SIZES[self.style.size]
        inset = 0.62 if dash is DashStyle.DRAW else 0

        def clamp_x(x: float) -> float:
            return max(0, min(w, x))

        def clamp_y(y: float) -> float:
            return max(0, min(h, y))

        return [
            (
                (clamp_x(sw * inset), clamp_y(sw * inset)),
                (clamp_x(w - sw * inset), clamp_y(h - sw * inset)),
            ),
            (
                (clamp_x(sw * inset), clamp_y(h - sw * inset)),
                (clamp_x(w - sw * inset), clamp_y(sw * inset)),
            ),
        ]


def rounded_polygon_points(
    id: str, outline: Sequence[vec.S], offset: float, roundness: float, passes: int
) -> List[vec.V]:
    results = []
    random = Random(id)
    p0 = outline[0]
    p1: vec.V

    for i in range(0, len(outline) * passes):
        p1 = vec.add(
            outline[(i + 1) % len(outline)],
            (random.uniform(-offset, offset), random.uniform(-offset, offset)),
        )

        delta = vec.sub(p1, p0)
        distance = vec.vlen(delta)
        vector = vec.mul(vec.div(delta, distance), min(distance / 4, roundness))
        results.append(vec.add(p0, vector))
        results.append(vec.add(p1, vec.neg(vector)))
        results.append(p1)

        p0 = p1

    return results


def rounded_inky_polygon_path(
    ctx: cairo.Context[CairoSomeSurface], points: Sequence[vec.S]
) -> None:
    points_iter = iter(points)

    start = next(points_iter)
    ctx.move_to(*start)

    try:
        while True:
            qp0 = next(points_iter)
            qp1 = next(points_iter)
            qp2 = next(points_iter, start)
            ctx.line_to(*qp0)

            cp1, cp2 = bezier_quad_to_cube(qp0, qp1, qp2)
            ctx.curve_to(*cp1, *cp2, *qp2)
    except StopIteration:
        pass
    ctx.close_path()


def geo_draw_polygon(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    style: Style,
    outline: Sequence[vec.S],
    lines: Sequence[Sequence[vec.S]],
) -> None:
    stroke_width = STROKE_SIZES[style.size]
    inner_polygon_points = rounded_polygon_points(id, outline, 0, stroke_width * 2, 1)
    rounded_inky_polygon_path(ctx, inner_polygon_points)
    apply_geo_fill(ctx, style)

    polygon_points = rounded_polygon_points(
        id, outline, stroke_width / 3, stroke_width * 2, 2
    )
    rounded_inky_polygon_path(ctx, polygon_points)

    for (a, b) in lines:
        ctx.move_to(*a)
        ctx.line_to(*b)

    ctx.set_source_rgb(*COLORS[style.color])
    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def geo_solid_polygon(
    ctx: cairo.Context[CairoSomeSurface],
    style: Style,
    outline: Sequence[vec.S],
    lines: Sequence[Sequence[vec.S]],
) -> None:
    ctx.move_to(*outline[0])
    for (x, y) in outline[1:]:
        ctx.line_to(x, y)
    ctx.close_path()
    apply_geo_fill(ctx, style, preserve_path=True)

    for (a, b) in lines:
        ctx.move_to(*a)
        ctx.line_to(*b)

    ctx.set_source_rgb(*COLORS[style.color])
    ctx.set_line_width(STROKE_SIZES[style.size])
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.stroke()


def geo_dash_polygon(
    ctx: cairo.Context[CairoSomeSurface],
    style: Style,
    outline: Sequence[vec.S],
    lines: Sequence[Sequence[vec.S]],
) -> None:
    stroke_width = STROKE_SIZES[style.size]
    ctx.move_to(*outline[0])
    for (x, y) in outline[1:]:
        ctx.line_to(x, y)
    ctx.close_path()
    apply_geo_fill(ctx, style)

    ctx.set_source_rgb(*COLORS[style.color])
    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    apply_geo_fill(ctx, style, preserve_path=True)

    for (a, b) in pairwise(chain(outline, outline[0:0])):
        ctx.move_to(*a)
        ctx.line_to(*b)

        dist = vec.dist(a, b)
        dash_array, dash_offset = get_perfect_dash_props(dist, stroke_width, style.dash)
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()

    for (a, b) in lines:
        ctx.move_to(*a)
        ctx.line_to(*b)

        dist = vec.dist(a, b)
        dash_array, dash_offset = get_perfect_dash_props(
            dist, stroke_width, style.dash, outset=False
        )
        ctx.set_dash(dash_array, dash_offset)
        ctx.stroke()
