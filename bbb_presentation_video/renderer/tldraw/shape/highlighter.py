# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import tau
from typing import TypeVar

import cairo

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    DrawShape,
    HighlighterShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    HIGHLIGHT_COLORS,
    STROKE_WIDTHS,
    draw_smooth_stroke_point_path,
    draw_stroke_points,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def finalize_highlight(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: HighlighterShape
) -> None:
    print(f"\tTldraw: Finalizing Highlight: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style
    is_complete = shape.isComplete

    stroke = HIGHLIGHT_COLORS[style.color]
    stroke_width = STROKE_WIDTHS[style.size] * 5
    opacity = 0.7

    # For very short lines, draw a point instead of a line
    size = shape.size
    very_small = size.width <= stroke_width / 2 and size.height <= stroke_width < 2

    if very_small:
        sw = 1 + stroke_width
        ctx.arc(0, 0, sw, 0, tau)
        ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, opacity)
        ctx.fill_preserve()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(1)
        ctx.stroke()
        return

    stroke_points = draw_stroke_points(shape.points, stroke_width, is_complete)

    draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)

    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_line_width(1 + stroke_width * 1.5)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, opacity)
    ctx.stroke()
