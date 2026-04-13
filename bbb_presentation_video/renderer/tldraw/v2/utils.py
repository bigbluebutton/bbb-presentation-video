# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import cos, inf, sin, tau
from typing import Dict, List, TypeVar

import cairo

from bbb_presentation_video.events.helpers import Color, Position
from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.utils import (
    ColorStyle,
    FillStyle,
    FontStyle,
    SizeStyle,
    Style,
    get_perfect_dash_props,
)

# SPDX-SnippetBegin
# SPDX-SnippetCopyrightText: 2024 BigBlueButton Inc. and by respective authors
# SPDX-SnippetCopyrightText: 2023 tldraw GB Ltd. <hello@tldraw.com>
# SPDX-License-Identifier: GPL-3.0-or-later AND Apache-2.0

# From tldraw shapes/shared/default-shape-constants.mjs
LINE_HEIGHT: float = 1.35
STROKE_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.S: 2,
    SizeStyle.M: 3.5,
    SizeStyle.L: 5,
    SizeStyle.XL: 10,
}
FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.S: 18,
    SizeStyle.M: 24,
    SizeStyle.L: 36,
    SizeStyle.XL: 44,
}
LABEL_FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.S: 18,
    SizeStyle.M: 22,
    SizeStyle.L: 26,
    SizeStyle.XL: 32,
}
ARROW_LABEL_FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.S: 18,
    SizeStyle.M: 20,
    SizeStyle.L: 24,
    SizeStyle.XL: 28,
}

# from tldraw utils/static-assets/assetUrls.ts
FONT_FAMILIES: Dict[FontStyle, str] = {
    FontStyle.DRAW: "Shantell Sans Normal, Semi-Bold",
    FontStyle.SERIF: "IBM Plex Serif, Medium",
    FontStyle.SANS: "IBM Plex Sans, Medium",
    FontStyle.MONO: "IBM Plex Mono, Medium",
}

# From tlschema styles/TLColorStyle.mjs
TEXT_COLOR: Color = Color.from_int(0x000000)
BACKGROUND_COLOR: Color = Color.from_int(0xF9FAFB)
SOLID_COLOR: Color = Color.from_int(0xFCFFFE)
COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.BLACK: Color.from_int(0x1D1D1D),
    ColorStyle.BLUE: Color.from_int(0x4263EB),
    ColorStyle.GREEN: Color.from_int(0x099268),
    ColorStyle.GREY: Color.from_int(0xADB5BD),
    ColorStyle.LIGHT_BLUE: Color.from_int(0x4DABF7),
    ColorStyle.LIGHT_GREEN: Color.from_int(0x40C057),
    ColorStyle.LIGHT_RED: Color.from_int(0xFF8787),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0xE599F7),
    ColorStyle.ORANGE: Color.from_int(0xF76707),
    ColorStyle.RED: Color.from_int(0xE03131),
    ColorStyle.VIOLET: Color.from_int(0xAE3EC9),
    ColorStyle.YELLOW: Color.from_int(0xFFC078),
}
SEMI_COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.BLACK: Color.from_int(0xE8E8E8),
    ColorStyle.BLUE: Color.from_int(0xDCE1F8),
    ColorStyle.GREEN: Color.from_int(0xD3E9E3),
    ColorStyle.GREY: Color.from_int(0xECEEF0),
    ColorStyle.LIGHT_BLUE: Color.from_int(0xDDEDFA),
    ColorStyle.LIGHT_GREEN: Color.from_int(0xDBF0E0),
    ColorStyle.LIGHT_RED: Color.from_int(0xF4DADB),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0xF5EAFA),
    ColorStyle.ORANGE: Color.from_int(0xF8E2D4),
    ColorStyle.RED: Color.from_int(0xF4DADB),
    ColorStyle.VIOLET: Color.from_int(0xECDCF2),
    ColorStyle.YELLOW: Color.from_int(0xF9F0E6),
}
PATTERN_COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.BLACK: Color.from_int(0x494949),
    ColorStyle.BLUE: Color.from_int(0x6681EE),
    ColorStyle.GREEN: Color.from_int(0x39A785),
    ColorStyle.GREY: Color.from_int(0xBCC3C9),
    ColorStyle.LIGHT_BLUE: Color.from_int(0x6FBBF8),
    ColorStyle.LIGHT_GREEN: Color.from_int(0x65CB78),
    ColorStyle.LIGHT_RED: Color.from_int(0xFE9E9E),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0xE9ACF8),
    ColorStyle.ORANGE: Color.from_int(0xF78438),
    ColorStyle.RED: Color.from_int(0xE55959),
    ColorStyle.VIOLET: Color.from_int(0xBD63D3),
    ColorStyle.YELLOW: Color.from_int(0xFECB92),
}
HIGHLIGHT_COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.BLACK: Color.from_int(
        0xFDDD00
    ),  # NOTE: Actually yellow (default highlighter)
    ColorStyle.BLUE: Color.from_int(0x10ACFF),
    ColorStyle.GREEN: Color.from_int(0x00FFC8),
    ColorStyle.GREY: Color.from_int(0xCBE7F1),
    ColorStyle.LIGHT_BLUE: Color.from_int(0x00F4FF),
    ColorStyle.LIGHT_GREEN: Color.from_int(0x65F641),
    ColorStyle.LIGHT_RED: Color.from_int(0xFF7FA3),
    ColorStyle.LIGHT_VIOLET: Color.from_int(0xFF88FF),
    ColorStyle.ORANGE: Color.from_int(0xFFA500),
    ColorStyle.RED: Color.from_int(0xFF636E),
    ColorStyle.VIOLET: Color.from_int(0xC77CFF),
    ColorStyle.YELLOW: Color.from_int(0xFDDD00),
}

# From tldraw editor/editor.css
FRAME_HEADING_FONT_SIZE: float = 12
FRAME_HEADING_PADDING: float = 8  # var(--space3)
FRAME_HEADING_BORDER_RADIUS: float = 4  # var(--radius-1)

NOTE_BORDER_RADIUS: float = 6  # var(--radius-2)

# SPDX-SnippetEnd

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def pattern_fill(color: ColorStyle) -> cairo.SurfacePattern:
    region = cairo.Rectangle(0, 0, 8, 8)
    surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, region)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(*BACKGROUND_COLOR)
    ctx.paint()

    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*PATTERN_COLORS[color])

    lines = [
        (0.66, 2, 2, 0.66),
        (3.33, 4.66, 4.66, 3.33),
        (6, 7.33, 7.33, 6),
    ]

    for x1, y1, x2, y2 in lines:
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)

    ctx.set_line_width(2)
    ctx.stroke()

    pattern = cairo.SurfacePattern(surface)
    pattern.set_extend(cairo.EXTEND_REPEAT)

    return pattern


def apply_geo_fill(
    ctx: cairo.Context[CairoSomeSurface], style: Style, preserve_path: bool = False
) -> None:
    if style.fill is FillStyle.NONE:
        if not preserve_path:
            ctx.new_path()
        return
    elif style.fill is FillStyle.SEMI:
        ctx.set_source_rgb(*SOLID_COLOR)
    elif style.fill is FillStyle.SOLID:
        ctx.set_source_rgb(*SEMI_COLORS[style.color])
    elif style.fill is FillStyle.PATTERN:
        pattern = pattern_fill(style.color)
        ctx.set_source(pattern)

    if preserve_path:
        ctx.fill_preserve()
    else:
        ctx.fill()


def finalize_geo_path(
    ctx: cairo.Context[CairoSomeSurface],
    points: List[Position],
    style: Style,
) -> None:

    dist: float = 0
    ctx.move_to(points[0].x, points[0].y)

    for i in range(1, len(points)):
        dist += vec.dist(points[i - 1], points[i])
        ctx.line_to(points[i].x, points[i].y)

    dist += vec.dist(points[-1], points[0])
    ctx.close_path()

    if style.isFilled:
        apply_geo_fill(ctx, style, preserve_path=True)

    stroke_width = STROKE_SIZES[style.size]

    ctx.set_line_width(stroke_width)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(*COLORS[style.color])

    # TODO: on geo shapes, perfect dash properties are actually supposed to be calculated per line segment
    dash_array, dash_offset = get_perfect_dash_props(dist, stroke_width, style.dash)

    ctx.set_dash(dash_array, dash_offset)
    ctx.stroke()


def polygon_vertices(width: float, height: float, sides: int) -> List[vec.V]:
    cx = width / 2
    cy = height / 2
    points_on_perimeter = []
    min_x = inf
    min_y = inf
    for i in range(0, sides):
        step = tau / sides
        t = -tau / 4 + i * step
        x = cx + cx * cos(t)
        y = cy + cy * sin(t)
        if x < min_x:
            min_x = x
        if y < min_y:
            min_y = y
        points_on_perimeter.append((x, y))

    if min_x != 0 or min_y != 0:
        points_on_perimeter = [(x - min_x, y - min_y) for (x, y) in points_on_perimeter]

    return points_on_perimeter
