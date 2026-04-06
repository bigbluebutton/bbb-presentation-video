# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, TypeVar

if TYPE_CHECKING:
    from bbb_presentation_video.renderer.tldraw import TldrawRenderer

import cairo

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw.shape import FrameShape, Shape
from bbb_presentation_video.renderer.tldraw.v2.shape.text import finalize_frame_name
from bbb_presentation_video.renderer.tldraw.v2.utils import SOLID_COLOR, TEXT_COLOR

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def dash_frame(
    self: TldrawRenderer[Any],
    ctx: cairo.Context[CairoSomeSurface],
    shape: FrameShape,
    frame_map: Dict[str, List[Shape]],
) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    points = [Position(0, 0), Position(w, 0), Position(w, h), Position(0, h)]

    # Create path for both fill and stroke
    ctx.move_to(points[0].x, points[0].y)
    for point in points[1:]:
        ctx.line_to(point.x, point.y)
    ctx.close_path()

    # Fill the path with the fill color
    ctx.set_source_rgb(*SOLID_COLOR)
    ctx.fill_preserve()

    # Stroke the path
    ctx.set_line_width(1)
    ctx.set_line_cap(cairo.LineCap.ROUND)
    ctx.set_line_join(cairo.LineJoin.ROUND)
    ctx.set_source_rgb(*TEXT_COLOR)
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

    # Recursively finalize the children.
    for child in children:
        self.finalize_shapes(ctx, child.id, child, frame_map)

    ctx.reset_clip()


def finalize_frame(
    self: TldrawRenderer[Any],
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: FrameShape,
    frame_map: Dict[str, List[Shape]],
) -> None:
    print(f"\tTldraw: Finalizing frame shape: {id}")

    ctx.push_group()

    ctx.rotate(shape.rotation)
    dash_frame(self, ctx, shape, frame_map)

    finalize_frame_name(ctx, shape)

    ctx.pop_group_to_source()
    ctx.paint_with_alpha(shape.style.opacity)
