# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum
from math import floor, inf, pi, sqrt
from typing import Dict, List, Sequence, Tuple, Union

import cairo
import perfect_freehand
from attrs import define

from bbb_presentation_video.events.helpers import Color, color_blend
from bbb_presentation_video.renderer.tldraw import vec


@define
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: float
    height: float


CANVAS: Color = Color.from_int(0xFAFAFA)


class SizeStyle(Enum):
    SMALL: str = "small"
    MEDIUM: str = "medium"
    LARGE: str = "large"


STROKE_WIDTHS: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 2.0,
    SizeStyle.MEDIUM: 3.5,
    SizeStyle.LARGE: 5.0,
}

FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 28,
    SizeStyle.MEDIUM: 48,
    SizeStyle.LARGE: 96,
}


class ColorStyle(Enum):
    WHITE: str = "white"
    LIGHT_GRAY: str = "lightGray"
    GRAY: str = "gray"
    BLACK: str = "black"
    GREEN: str = "green"
    CYAN: str = "cyan"
    BLUE: str = "blue"
    INDIGO: str = "indigo"
    VIOLET: str = "violet"
    RED: str = "red"
    ORANGE: str = "orange"
    YELLOW: str = "yellow"


STROKES: Dict[ColorStyle, Color] = {
    ColorStyle.WHITE: Color.from_int(0x1D1D1D),
    ColorStyle.LIGHT_GRAY: Color.from_int(0xC6CBD1),
    ColorStyle.GRAY: Color.from_int(0x788492),
    ColorStyle.BLACK: Color.from_int(0x1D1D1D),
    ColorStyle.GREEN: Color.from_int(0x36B24D),
    ColorStyle.CYAN: Color.from_int(0x0E98AD),
    ColorStyle.BLUE: Color.from_int(0x1C7ED6),
    ColorStyle.INDIGO: Color.from_int(0x4263EB),
    ColorStyle.VIOLET: Color.from_int(0x7746F1),
    ColorStyle.RED: Color.from_int(0xFF2133),
    ColorStyle.ORANGE: Color.from_int(0xFF9433),
    ColorStyle.YELLOW: Color.from_int(0xFFC936),
}

FILLS: Dict[ColorStyle, Color] = dict(
    [
        (
            k,
            color_blend(v, CANVAS, 0.82)
            if k is not ColorStyle.WHITE
            else Color.from_int(0xFEFEFE),
        )
        for k, v in STROKES.items()
    ]
)


class DashStyle(Enum):
    DRAW: str = "draw"
    SOLID: str = "solid"
    DASHED: str = "dashed"
    DOTTED: str = "dotted"


class FontStyle(Enum):
    SCRIPT: str = "script"
    SANS: str = "sans"
    ERIF: str = "erif"  # SIC
    SERIF: str = "serif"  # In case they fix the spelling
    MONO: str = "mono"


FONT_FACES: Dict[FontStyle, str] = {
    FontStyle.SCRIPT: "Caveat Brush",
    FontStyle.SANS: "Source Sans Pro",
    FontStyle.ERIF: "Crimson Pro",
    FontStyle.SERIF: "Crimson Pro",
    FontStyle.MONO: "Source Code Pro",
}


class AlignStyle(Enum):
    START: str = "start"
    MIDDLE: str = "middle"
    END: str = "end"
    JUSTIFY: str = "justify"


@define
class Style:
    color: ColorStyle = ColorStyle.BLACK
    size: SizeStyle = SizeStyle.SMALL
    dash: DashStyle = DashStyle.DRAW
    isFilled: bool = False
    scale: float = 1
    font: FontStyle = FontStyle.SCRIPT
    textAlign: AlignStyle = AlignStyle.MIDDLE


def get_bounds_from_points(
    points: Sequence[Union[Tuple[float, float], Tuple[float, float, float]]]
) -> Bounds:
    min_x = min_y = inf
    max_x = max_y = -inf

    if len(points) == 0:
        min_x = min_y = max_x = max_y = 0

    for point in points:
        x = point[0]
        y = point[1]
        min_x = min(x, min_x)
        min_y = min(y, min_y)
        max_x = max(x, max_x)
        max_y = max(y, max_y)

    return Bounds(min_x, min_y, max_x, max_y, max_x - min_x, max_y - min_y)


def perimeter_of_ellipse(rx: float, ry: float) -> float:
    """Find the approximate perimeter of an ellipse."""
    h = (rx - ry) ** 2 / (rx + ry) ** 2
    return pi * (rx + ry) * (1 + (3 * h) / (10 + sqrt(4 - 3 * h)))


def draw_stroke_points(
    points: Sequence[Tuple[float, float]], stroke_width: float, is_complete: bool
) -> List[perfect_freehand.types.StrokePoint]:
    return perfect_freehand.get_stroke_points(
        points,
        size=1 + stroke_width * 1.5,
        streamline=0.65,
        last=is_complete,
    )


def get_perfect_dash_props(
    length: float,
    stroke_width: float,
    style: DashStyle,
    snap: int = 1,
    outset: bool = True,
    length_ratio: float = 2,
) -> Tuple[List[float], float]:

    if style is DashStyle.DASHED:
        dash_length = stroke_width * length_ratio
        ratio = 1
        offset = dash_length / 2 if outset else 0
    elif style is DashStyle.DOTTED:
        dash_length = stroke_width / 100
        ratio = 100
        offset = 0
    else:
        return ([], 0)

    dashes = floor(length / dash_length / (2 * ratio))
    dashes -= dashes % snap
    dashes = max(dashes, 4)

    gap_length = max(
        dash_length,
        (length - dashes * dash_length) / (dashes if outset else dashes - 1),
    )

    return ([dash_length, gap_length], offset)


def bezier_quad_to_cube(
    qp0: Tuple[float, float], qp1: Tuple[float, float], qp2: Tuple[float, float]
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    return (
        vec.add(qp0, vec.mul(vec.sub(qp1, qp0), 2 / 3)),
        vec.add(qp2, vec.mul(vec.sub(qp1, qp2), 2 / 3)),
    )


def draw_smooth_path(
    ctx: cairo.Context, points: Sequence[Tuple[float, float]], closed: bool = True
) -> None:
    """Turn an array of points into a path of quadratic curves."""

    if len(points) < 1:
        return

    prev_point = points[0]
    if closed:
        prev_mid = vec.med(points[-1], prev_point)
    else:
        prev_mid = prev_point
    ctx.move_to(prev_mid[0], prev_mid[1])
    for point in points[1:]:
        mid = vec.med(prev_point, point)
        print(
            f"Prev Mid: {prev_mid}, Prev Point: {prev_point}, Mid: {mid}, Point: {point}"
        )

        # Cairo can't render quadratic curves directly, need to convert to cubic curves.
        cp1, cp2 = bezier_quad_to_cube(prev_mid, prev_point, mid)
        ctx.curve_to(cp1[0], cp1[1], cp2[0], cp2[1], mid[0], mid[1])
        prev_point = point
        prev_mid = mid

    if closed:
        point = points[0]
        mid = vec.med(prev_point, point)
    else:
        point = points[-1]
        mid = point

    print(f"Prev Mid: {prev_mid}, Prev Point: {prev_point}, Mid: {mid}, Point: {point}")

    cp1, cp2 = bezier_quad_to_cube(prev_mid, prev_point, mid)
    ctx.curve_to(cp1[0], cp1[1], cp2[0], cp2[1], mid[0], mid[1])

    if closed:
        ctx.close_path()


def draw_smooth_stroke_point_path(
    ctx: cairo.Context,
    points: Sequence[perfect_freehand.types.StrokePoint],
    closed: bool = True,
) -> None:
    outline_points = list(map(lambda p: p["point"], points))
    draw_smooth_path(ctx, outline_points, closed)
