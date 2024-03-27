# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from bbb_presentation_video.renderer.tldraw import TldrawRenderer
import cairo
from bbb_presentation_video.events.helpers import Position

from bbb_presentation_video.renderer.tldraw.shape import FrameShape
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_frame_name
from bbb_presentation_video.renderer.tldraw.utils import (
    COLORS,
    STROKES,
    ColorStyle,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def dash_frame(
    self: TldrawRenderer[Any], ctx: cairo.Context[CairoSomeSurface], shape: FrameShape
) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    points = [Position(0, 0), Position(w, 0), Position(w, h), Position(0, h)]

    # Set up fill color
    fill = COLORS[ColorStyle.SEMI]
    ctx.set_source_rgba(fill.r, fill.g, fill.b, style.opacity)

    # Create path for both fill and stroke
    ctx.move_to(points[0].x, points[0].y)
    for point in points[1:]:
        ctx.line_to(point.x, point.y)
    ctx.close_path()

    # Fill the path with the fill color
    ctx.fill_preserve()

    # Set up stroke
    stroke = STROKES[ColorStyle.BLACK]
    sw = 2
    ctx.set_line_width(sw)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)

    # Stroke the path
    ctx.stroke()

    # Define the clipping path (same as the frame shape)
    ctx.new_path()
    ctx.move_to(0, 0)
    ctx.line_to(w, 0)
    ctx.line_to(w, h)
    ctx.line_to(0, h)
    ctx.close_path()
    ctx.clip()

    children = shape.children

    for child in children:
        self.finalize_shapes(ctx, child.id, child)

    ctx.reset_clip()


def finalize_frame(
    self: TldrawRenderer[Any],
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: FrameShape,
) -> None:
    print(f"\tTldraw: Finalizing frame shape: {id}")

    ctx.rotate(shape.rotation)
    dash_frame(self, ctx, shape)

    finalize_frame_name(ctx, shape)
