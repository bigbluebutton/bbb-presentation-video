# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import math
from enum import Enum
from math import ceil, cos, floor, hypot, pi, sin, sqrt, tau
from random import Random
from typing import Dict, List, Optional, Sequence, Tuple, TypeVar, Union

import attr
import cairo
import gi
import perfect_freehand

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

from bbb_presentation_video.events.helpers import Color, Position, Size, color_blend
from bbb_presentation_video.events.tldraw import StyleData
from bbb_presentation_video.renderer.tldraw import vec

DrawPoints = List[Union[Tuple[float, float], Tuple[float, float, float]]]

CANVAS: Color = Color.from_int(0xFAFAFA)

PATTERN_FILL_BACKGROUND_COLOR: Color = Color.from_int(0xFCFFFE)
STICKY_TEXT_COLOR: Color = Color.from_int(0x0D0D0D)
STICKY_PADDING: float = 16.0


class SizeStyle(Enum):
    SMALL = "small"
    S = "s"
    MEDIUM = "medium"
    M = "m"
    LARGE = "large"
    L = "l"
    XL = "xl"


STROKE_WIDTHS: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 2.0,
    SizeStyle.S: 2.0,
    SizeStyle.MEDIUM: 3.5,
    SizeStyle.M: 3.5,
    SizeStyle.LARGE: 5.0,
    SizeStyle.L: 5.0,
    SizeStyle.XL: 6.5,
}

FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 28,
    SizeStyle.S: 26,
    SizeStyle.MEDIUM: 48,
    SizeStyle.M: 36,
    SizeStyle.LARGE: 96,
    SizeStyle.L: 54,
    SizeStyle.XL: 64,
}

STICKY_FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 24,
    SizeStyle.S: 24,
    SizeStyle.MEDIUM: 36,
    SizeStyle.M: 36,
    SizeStyle.LARGE: 48,
    SizeStyle.L: 48,
    SizeStyle.XL: 60,
}

LETTER_SPACING: float = -0.03  # em


class ColorStyle(Enum):
    WHITE = "white"
    LIGHT_GRAY = "lightGray"
    GRAY = "gray"
    GREY = "grey"
    BLACK = "black"
    GREEN = "green"
    LIGHT_GREEN = "light-green"
    CYAN = "cyan"
    BLUE = "blue"
    LIGHT_BLUE = "light-blue"
    INDIGO = "indigo"
    VIOLET = "violet"
    LIGHT_VIOLET = "light-violet"
    RED = "red"
    LIGHT_RED = "light-red"
    ORANGE = "orange"
    YELLOW = "yellow"
    SEMI = "semi"


COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.WHITE: Color.from_int(0x1D1D1D),
    ColorStyle.LIGHT_GRAY: Color.from_int(0xC6CBD1),
    ColorStyle.GRAY: Color.from_int(0x788492),
    ColorStyle.GREY: Color.from_int(0x9EA6B0),
    ColorStyle.BLACK: Color.from_int(0x1D1D1D),
    ColorStyle.GREEN: Color.from_int(0x36B24D),
    ColorStyle.LIGHT_GREEN: Color.from_int(0x38B845),
    ColorStyle.CYAN: Color.from_int(0x0E98AD),
    ColorStyle.BLUE: Color.from_int(0x1C7ED6),
    ColorStyle.LIGHT_BLUE: Color.from_int(0x4099F5),
    ColorStyle.INDIGO: Color.from_int(0x4263EB),
    ColorStyle.VIOLET: Color.from_int(0x7746F1),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0x9C1FBE),
    ColorStyle.RED: Color.from_int(0xFF2133),
    ColorStyle.LIGHT_RED: Color.from_int(0xFC7075),
    ColorStyle.ORANGE: Color.from_int(0xFF9433),
    ColorStyle.YELLOW: Color.from_int(0xFFC936),
    ColorStyle.SEMI: Color.from_int(0xF5F9F7),
}

HIGHLIGHT_COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.BLACK: Color.from_int(0xFFF4A1),
    ColorStyle.GREY: Color.from_int(0xEDF7FA),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0xFFD7FF),
    ColorStyle.VIOLET: Color.from_int(0xECD3FF),
    ColorStyle.BLUE: Color.from_int(0xB4E2FF),
    ColorStyle.LIGHT_BLUE: Color.from_int(0xA2FCFF),
    ColorStyle.YELLOW: Color.from_int(0xFFF4A1),
    ColorStyle.ORANGE: Color.from_int(0xFFE2B5),
    ColorStyle.GREEN: Color.from_int(0xA2FFEC),
    ColorStyle.LIGHT_GREEN: Color.from_int(0xCCFCC1),
    ColorStyle.LIGHT_RED: Color.from_int(0xFFD3DF),
    ColorStyle.RED: Color.from_int(0xFFCACD),
}


STICKY_FILLS: Dict[ColorStyle, Color] = dict(
    [
        (
            k,
            (
                Color.from_int(0xFFFFFF)
                if k is ColorStyle.WHITE
                else (
                    Color.from_int(0x3D3D3D)
                    if k is ColorStyle.BLACK
                    else color_blend(v, CANVAS, 0.45)
                )
            ),
        )
        for k, v in COLORS.items()
    ]
)

STROKES: Dict[ColorStyle, Color] = dict(
    [
        (k, Color.from_int(0x1D1D1D) if k is ColorStyle.WHITE else v)
        for k, v in COLORS.items()
    ]
)

FILLS: Dict[ColorStyle, Color] = dict(
    [
        (
            k,
            (
                Color.from_int(0xFEFEFE)
                if k is ColorStyle.WHITE
                else color_blend(v, CANVAS, 0.82)
            ),
        )
        for k, v in COLORS.items()
    ]
)

V2_TEXT_COLOR: Color = Color.from_int(0x000000)


@attr.s(order=False, slots=True, auto_attribs=True)
class V2Color:
    solid: Color
    semi: Color
    pattern: Color
    highlight: Color


V2_COLORS: Dict[ColorStyle, V2Color] = {
    ColorStyle.BLACK: V2Color(
        solid=Color.from_int(0x1D1D1D),
        semi=Color.from_int(0xE8E8E8),
        pattern=Color.from_int(0x494949),
        highlight=Color.from_int(0xFDDD00),
    ),
    ColorStyle.BLUE: V2Color(
        solid=Color.from_int(0x4263EB),
        semi=Color.from_int(0xDCE1F8),
        pattern=Color.from_int(0x6681EE),
        highlight=Color.from_int(0x10ACFF),
    ),
    ColorStyle.GREEN: V2Color(
        solid=Color.from_int(0x099268),
        semi=Color.from_int(0xD3E9E3),
        pattern=Color.from_int(0x39A785),
        highlight=Color.from_int(0x00FFC8),
    ),
    ColorStyle.GREY: V2Color(
        solid=Color.from_int(0xADB5BD),
        semi=Color.from_int(0xECEEF0),
        pattern=Color.from_int(0xBCC3C9),
        highlight=Color.from_int(0xCBE7F1),
    ),
    ColorStyle.LIGHT_BLUE: V2Color(
        solid=Color.from_int(0x4DABF7),
        semi=Color.from_int(0xDDEDFA),
        pattern=Color.from_int(0x6FBBF8),
        highlight=Color.from_int(0x00F4FF),
    ),
    ColorStyle.LIGHT_GREEN: V2Color(
        solid=Color.from_int(0x40C057),
        semi=Color.from_int(0xDBF0E0),
        pattern=Color.from_int(0x65CB78),
        highlight=Color.from_int(0x65F641),
    ),
    ColorStyle.LIGHT_RED: V2Color(
        solid=Color.from_int(0xFF8787),
        semi=Color.from_int(0xF4DADB),
        pattern=Color.from_int(0xFE9E9E),
        highlight=Color.from_int(0xFF7FA3),
    ),
    ColorStyle.LIGHT_VIOLET: V2Color(
        solid=Color.from_int(0xE599F7),
        semi=Color.from_int(0xF5EAFA),
        pattern=Color.from_int(0xE9ACF8),
        highlight=Color.from_int(0xFF88FF),
    ),
    ColorStyle.ORANGE: V2Color(
        solid=Color.from_int(0xF76707),
        semi=Color.from_int(0xF8E2D4),
        pattern=Color.from_int(0xF78438),
        highlight=Color.from_int(0xFFA500),
    ),
    ColorStyle.RED: V2Color(
        solid=Color.from_int(0xE03131),
        semi=Color.from_int(0xF4DADB),
        pattern=Color.from_int(0xE55959),
        highlight=Color.from_int(0xFF636E),
    ),
    ColorStyle.VIOLET: V2Color(
        solid=Color.from_int(0xAE3EC9),
        semi=Color.from_int(0xECDCF2),
        pattern=Color.from_int(0xBD63D3),
        highlight=Color.from_int(0xC77CFF),
    ),
    ColorStyle.YELLOW: V2Color(
        solid=Color.from_int(0xFFC078),
        semi=Color.from_int(0xF9F0E6),
        pattern=Color.from_int(0xFECB92),
        highlight=Color.from_int(0xFDDD00),
    ),
}


class DashStyle(Enum):
    DRAW = "draw"
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"


class FontStyle(Enum):
    SCRIPT = "script"
    SANS = "sans"
    ERIF = "erif"  # Old tldraw versions had this spelling mistake
    SERIF = "serif"
    MONO = "mono"
    DRAW = "draw"
    ARIAL = "arial"


FONT_FACES: Dict[FontStyle, str] = {
    FontStyle.SCRIPT: "Caveat Brush",
    FontStyle.SANS: "Source Sans Pro",
    FontStyle.ERIF: "Crimson Pro",
    FontStyle.SERIF: "Crimson Pro",
    FontStyle.MONO: "Source Code Pro",
    FontStyle.DRAW: "Caveat Brush",
    FontStyle.ARIAL: "Arial",
}


class AlignStyle(Enum):
    START = "start"
    MIDDLE = "middle"
    END = "end"
    JUSTIFY = "justify"


class FillStyle(Enum):
    NONE = "none"
    SEMI = "semi"
    SOLID = "solid"
    PATTERN = "pattern"


@attr.s(order=False, slots=True, auto_attribs=True)
class Style:
    color: ColorStyle = ColorStyle.BLACK
    size: SizeStyle = SizeStyle.SMALL
    dash: DashStyle = DashStyle.DRAW
    isFilled: bool = False
    isClosed: bool = False
    scale: float = 1
    font: FontStyle = FontStyle.SCRIPT
    textAlign: AlignStyle = AlignStyle.MIDDLE
    opacity: float = 1
    fill: FillStyle = FillStyle.NONE

    def update_from_data(self, data: StyleData) -> None:
        if "color" in data:
            self.color = ColorStyle(data["color"])
        if "size" in data:
            self.size = SizeStyle(data["size"])
        if "dash" in data:
            self.dash = DashStyle(data["dash"])
        if "isFilled" in data:
            self.isFilled = data["isFilled"]
        if "scale" in data:
            self.scale = data["scale"]
        if "font" in data:
            self.font = FontStyle(data["font"])
        if "textAlign" in data:
            self.textAlign = AlignStyle(data["textAlign"])
        if "opacity" in data:
            self.opacity = data["opacity"]

        # Tldraw v2 style props not present in v1
        if "isClosed" in data:
            self.isClosed = data["isClosed"]
        if "fill" in data:
            self.fill = FillStyle(data["fill"])
            if self.fill is not FillStyle.NONE:
                self.isFilled = True


class Decoration(Enum):
    ARROW = "arrow"
    BAR = "bar"
    DIAMOND = "diamond"
    DOT = "dot"
    INVERTED = "inverted"
    NONE = "none"
    SQUARE = "square"
    TRIANGLE = "triangle"


class SplineType(Enum):
    CUBIC = "cubic"
    LINE = "line"
    NONE = "none"


def perimeter_of_ellipse(rx: float, ry: float) -> float:
    """Find the approximate perimeter of an ellipse."""

    # Handle degenerate case where the "ellipse" is actually a line or a point
    if rx == 0:
        return 2 * ry
    elif ry == 0:
        return 2 * rx

    h = (rx - ry) ** 2 / (rx + ry) ** 2
    return pi * (rx + ry) * (1 + (3 * h) / (10 + sqrt(4 - 3 * h)))


def circle_from_three_points(
    A: Sequence[float], B: Sequence[float], C: Sequence[float]
) -> Tuple[Position, float]:
    """Get a circle from three points."""
    (x1, y1) = A
    (x2, y2) = B
    (x3, y3) = C

    a = x1 * (y2 - y3) - y1 * (x2 - x3) + x2 * y3 - x3 * y2

    b = (
        (x1 * x1 + y1 * y1) * (y3 - y2)
        + (x2 * x2 + y2 * y2) * (y1 - y3)
        + (x3 * x3 + y3 * y3) * (y2 - y1)
    )

    c = (
        (x1 * x1 + y1 * y1) * (x2 - x3)
        + (x2 * x2 + y2 * y2) * (x3 - x1)
        + (x3 * x3 + y3 * y3) * (x1 - x2)
    )

    x = -b / (2 * a)

    y = -c / (2 * a)

    return (Position(x, y), hypot(x - x1, y - y1))


def short_angle_dist(a0: float, a1: float) -> float:
    """Get the short angle distance between two angles."""
    max = math.pi * 2
    da = (a1 - a0) % max
    return ((2 * da) % max) - da


def lerp_angles(a0: float, a1: float, t: float) -> float:
    """Interpolate an angle between two angles."""
    return a0 + short_angle_dist(a0, a1) * t


def get_sweep(C: Sequence[float], A: Sequence[float], B: Sequence[float]) -> float:
    """Get the "sweep" or short distance between two points on a circle's perimeter."""
    return short_angle_dist(vec.angle(C, A), vec.angle(C, B))


def draw_stroke_points(
    points: DrawPoints, stroke_width: float, is_complete: bool
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
    qp0: Sequence[float], qp1: Sequence[float], qp2: Sequence[float]
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    return (
        vec.add(qp0, vec.mul(vec.sub(qp1, qp0), 2 / 3)),
        vec.add(qp2, vec.mul(vec.sub(qp1, qp2), 2 / 3)),
    )


def bezier_length(
    start: Position, control: Position, end: Position, num_segments: int = 10
) -> float:
    """Approximate the length of a cubic Bézier curve."""
    length = 0.0
    t_values = [i / num_segments for i in range(num_segments + 1)]
    last_point = start

    for t in t_values[1:]:
        # Calculate the next point on the curve
        x = (
            (1 - t) ** 3 * start.x
            + 3 * (1 - t) ** 2 * t * control.x
            + 3 * (1 - t) * t**2 * control.x
            + t**3 * end.x
        )
        y = (
            (1 - t) ** 3 * start.y
            + 3 * (1 - t) ** 2 * t * control.y
            + 3 * (1 - t) * t**2 * control.y
            + t**3 * end.y
        )
        next_point = Position(x, y)

        # Add the distance from the last point to the current point
        length += vec.dist(last_point, next_point)
        last_point = next_point

    return length


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def rounded_rect(
    ctx: cairo.Context[CairoSomeSurface], size: Size, radius: float
) -> None:
    ctx.new_sub_path()
    ctx.arc(size.width - radius, radius, radius, -tau / 4, 0)
    ctx.arc(size.width - radius, size.height - radius, radius, 0, tau / 4)
    ctx.arc(radius, size.height - radius, radius, tau / 4, tau / 2)
    ctx.arc(radius, radius, radius, tau / 2, -tau / 4)
    ctx.close_path()


def draw_smooth_path(
    ctx: cairo.Context[CairoSomeSurface],
    points: Sequence[Tuple[float, float]],
    closed: bool = True,
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

    cp1, cp2 = bezier_quad_to_cube(prev_mid, prev_point, mid)
    ctx.curve_to(cp1[0], cp1[1], cp2[0], cp2[1], mid[0], mid[1])

    if closed:
        ctx.close_path()


def draw_smooth_stroke_point_path(
    ctx: cairo.Context[CairoSomeSurface],
    points: Sequence[perfect_freehand.types.StrokePoint],
    closed: bool = True,
) -> None:
    outline_points = list(map(lambda p: p["point"], points))
    draw_smooth_path(ctx, outline_points, closed)


def get_arc_length(C: Position, r: float, A: Position, B: Position) -> float:
    sweep = get_sweep(C, A, B)
    return r * tau * (sweep / tau)


def get_polygon_strokes(
    width: float, height: float, sides: int
) -> List[Tuple[Position, Position, float]]:
    cx = width / 2
    cy = height / 2
    strokes = []

    for i in range(sides):
        step = tau / sides
        t = -(tau / 4) + i * step
        x = cx + cx * cos(t)
        y = cy + cy * sin(t)

        next_t = -(tau / 4) + ((i + 1) % sides) * step
        next_x = cx + cx * cos(next_t)
        next_y = cy + cy * sin(next_t)

        pos1 = Position(x, y)
        pos2 = Position(next_x, next_y)
        distance = ((pos2.x - pos1.x) ** 2 + (pos2.y - pos1.y) ** 2) ** 0.5

        strokes.append((pos1, pos2, distance))

    # Adjust positions to ensure the polygon fits within the bounding box starting from (0,0)
    min_x = min(stroke[0].x for stroke in strokes)
    min_y = min(stroke[0].y for stroke in strokes)

    for i in range(len(strokes)):
        stroke = strokes[i]
        strokes[i] = (
            Position(stroke[0].x - min_x, stroke[0].y - min_y),
            Position(stroke[1].x - min_x, stroke[1].y - min_y),
            stroke[2],
        )

    return strokes


def get_polygon_draw_vertices(
    strokes: List[Tuple[Position, Position, float]], stroke_width: float, id: str
) -> List[Tuple[float, float, float]]:
    random = Random(id)
    # Generate vertices with added variation
    variation = stroke_width * 0.75
    v_points = [
        (
            stroke[0].x + random.uniform(-variation, variation),
            stroke[0].y + random.uniform(-variation, variation),
        )
        for stroke in strokes
    ]

    # Determine the random start index for drawing
    rm = random.randrange(0, len(v_points))

    # Generate lines between points with added variation
    lines = [
        vec.points_between(v_points[i], v_points[(i + 1) % len(v_points)], 32)
        for i in range(len(v_points))
    ]

    lines = lines[rm:] + lines[:rm]

    # Flatten the list of lines to get a single list of points, ensuring the start point is duplicated at the end for closure
    points = []
    for line in lines:
        points.extend(line)

    points.extend(lines[0])  # Add start point again at the end
    return points


def get_point_on_circle(center: Position, radius: float, angle: float) -> Position:
    return Position(center[0] + radius * cos(angle), center[1] + radius * sin(angle))


# Set DPI to "72" so we're working directly in Pango point units.
DPI: float = 72.0


def create_pango_layout(
    ctx: cairo.Context[CairoSomeSurface],
    style: Style,
    font_description: str,
    font_size: float,
    *,
    width: Optional[float] = None,
    padding: float = 0,
    align: Optional[AlignStyle] = None,
    wrap: bool = True,
    letter_spacing: Optional[float] = LETTER_SPACING,
) -> Pango.Layout:
    print(
        f"\t\tPango layout: font_description={font_description}, font_size={font_size}, width={width}, padding={padding}, align={align}, wrap={wrap}"
    )
    pctx = PangoCairo.create_context(ctx)
    pctx.set_round_glyph_positions(False)

    font = Pango.FontDescription.from_string(font_description)
    font.set_size(round(font_size * style.scale * Pango.SCALE))

    fo = cairo.FontOptions()
    fo.set_antialias(cairo.Antialias.GRAY)
    fo.set_hint_metrics(cairo.HintMetrics.OFF)
    fo.set_hint_style(cairo.HintStyle.NONE)
    PangoCairo.context_set_font_options(pctx, fo)

    attrs = Pango.AttrList()
    if letter_spacing is not None:
        letter_spacing_attr = Pango.attr_letter_spacing_new(
            round(letter_spacing * font_size * style.scale * Pango.SCALE)
        )
        attrs.insert(letter_spacing_attr)
    insert_hyphens_attr = Pango.attr_insert_hyphens_new(insert_hyphens=False)
    attrs.insert(insert_hyphens_attr)

    layout = Pango.Layout(pctx)
    PangoCairo.context_set_resolution(pctx, DPI)
    layout.set_auto_dir(True)
    layout.set_attributes(attrs)
    layout.set_font_description(font)

    if align is None:
        align = style.textAlign

    if align == AlignStyle.START:
        layout.set_alignment(Pango.Alignment.LEFT)
    elif align == AlignStyle.MIDDLE:
        layout.set_alignment(Pango.Alignment.CENTER)
    elif align == AlignStyle.END:
        layout.set_alignment(Pango.Alignment.RIGHT)
    elif align == AlignStyle.JUSTIFY:
        layout.set_alignment(Pango.Alignment.LEFT)
        layout.set_justify(True)

    if width is not None:
        layout.set_width(ceil((width - (padding * 2)) * Pango.SCALE))

    if wrap:
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    else:
        layout.set_height(0)
        layout.set_ellipsize(Pango.EllipsizeMode.END)

    return layout


def show_layout_by_lines(
    ctx: cairo.Context[CairoSomeSurface],
    layout: Pango.Layout,
    *,
    padding: float = 0,
    do_path: bool = False,
    line_height: float = 1.0,
) -> None:
    """Show a Pango Layout line by line to manually handle CSS-style line height."""
    # TODO: With Pango 1.50 this can be replaced with Pango.attr_line_height_new_absolute

    font = layout.get_font_description()
    # Replicate CSS line-height being a multiplier of font size
    line_height = font.get_size() / Pango.SCALE * line_height

    ctx.save()
    ctx.translate(padding, padding)
    iter = layout.get_iter()
    while True:
        # Get the layout iter's line extents for horizontal positioning
        _ink_rect, logical_rect = iter.get_line_extents()
        offset_x = logical_rect.x / Pango.SCALE

        # Get the line's extents for vertical positioning
        line = iter.get_line_readonly()
        # With show_layout_line, text origin is at baseline. y is a negative number that
        # indicates how far the font extends above baseline, and height is a positive number
        # which is the font's natural line height.
        _ink_rect, logical_rect = line.get_extents()
        logical_y = logical_rect.y / Pango.SCALE
        logical_height = logical_rect.height / Pango.SCALE
        # For CSS line height adjustments, the "leading" value (difference between set line
        # height and font's natural line height) is split in half - half is added above, and
        # half below.
        # To get the baseline in the right position, we offset by the font ascent plus the
        # half-leading value.
        offset_y = (-logical_y) + (line_height - logical_height) / 2

        ctx.save()
        ctx.translate(offset_x, offset_y)
        if do_path:
            PangoCairo.layout_line_path(ctx, line)
        else:
            PangoCairo.show_layout_line(ctx, line)
        ctx.restore()

        ctx.translate(0, line_height)
        if not iter.next_line():
            break

    ctx.restore()


def get_layout_size(
    layout: Pango.Layout, *, padding: float = 0, line_height: float = 1.0
) -> Size:
    # TODO: Once we switch to Pango 1.50 and use Pango.attr_line_height_new_absolute this can
    # be replaced with a call to layout.get_size()
    layout_size = layout.get_size()
    width = layout_size[0] / Pango.SCALE
    lines = layout.get_line_count()
    font = layout.get_font_description()
    line_height = font.get_size() / Pango.SCALE * line_height
    height = lines * line_height
    return Size(width + padding * 2, height + padding * 2)
