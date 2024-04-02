# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.renderer.tldraw.shape import EllipseGeo
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import (
    STROKE_WIDTHS,
    STROKES,
    apply_geo_fill,
    get_perfect_dash_props,
    perimeter_of_ellipse,
)
from bbb_presentation_video.renderer.utils import cairo_draw_ellipse

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def dash_ellipse(ctx: cairo.Context[CairoSomeSurface], shape: EllipseGeo) -> None:
    radius = (shape.size.width / 2, shape.size.height / 2)
    style = shape.style
    stroke = STROKES[style.color]
    stroke_width = STROKE_WIDTHS[style.size]

    sw = 1 + stroke_width * 1.618
    rx = max(0, radius[0] - sw / 2)
    ry = max(0, radius[1] - sw / 2)
    perimeter = perimeter_of_ellipse(rx, ry)
    dash_array, dash_offset = get_perfect_dash_props(
        perimeter * 2 if perimeter < 64 else perimeter,
        stroke_width * 1.618,
        style.dash,
        snap=4,
    )

    if style.isFilled:
        cairo_draw_ellipse(ctx, radius[0], radius[1], radius[0], radius[1])
        apply_geo_fill(ctx, style)

    cairo_draw_ellipse(ctx, radius[0], radius[1], radius[0], radius[1])

    ctx.set_dash(dash_array, dash_offset)
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
    ctx.stroke()


def finalize_geo_ellipse(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: EllipseGeo,
) -> None:
    print(f"\tTldraw: Finalizing Ellipse (geo): {id}")

    ctx.rotate(shape.rotation)

    dash_ellipse(ctx, shape)

    finalize_v2_label(ctx, shape)
