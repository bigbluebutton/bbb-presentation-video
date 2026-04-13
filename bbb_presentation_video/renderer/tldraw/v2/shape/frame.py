# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, TypeVar

import attr

from bbb_presentation_video.renderer.tldraw.shape.proto import (
    BaseShapeProto,
    LabelledShapeProto,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    AlignStyle,
    FontStyle,
    create_pango_layout,
    get_layout_size,
    rounded_rect,
    show_layout_by_lines,
)

if TYPE_CHECKING:
    from bbb_presentation_video.renderer.tldraw import TldrawRenderer

import cairo

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.renderer.tldraw.v2.utils import (
    BACKGROUND_COLOR,
    FONT_FAMILIES,
    FRAME_HEADING_BORDER_RADIUS,
    FRAME_HEADING_FONT_SIZE,
    FRAME_HEADING_PADDING,
    SOLID_COLOR,
    TEXT_COLOR,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(order=False, slots=True, auto_attribs=True)
class FrameShape(LabelledShapeProto):
    # BaseShapeProto
    children: List[BaseShapeProto] = []
    # LabelledShapeProto
    label: str = "Frame"
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


def dash_frame(
    self: TldrawRenderer[Any],
    ctx: cairo.Context[CairoSomeSurface],
    shape: FrameShape,
    frame_map: Dict[str, List[BaseShapeProto]],
) -> None:
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


def finalize_frame_name(
    ctx: cairo.Context[CairoSomeSurface],
    shape: FrameShape,
) -> Size:
    if shape.label is None or shape.label == "":
        return Size(0, 0)

    print(f"\t\tFinalizing Frame name (v2)")

    style = shape.style

    ctx.save()

    # Create layout aligning the text to the top left
    layout = create_pango_layout(
        ctx,
        style,
        FONT_FAMILIES[FontStyle.SANS],
        FRAME_HEADING_FONT_SIZE,
        width=shape.size.width,
        padding=0,
        align=AlignStyle.START,
        letter_spacing=None,
    )

    layout.set_text(shape.label, -1)

    label_size = get_layout_size(layout, padding=FRAME_HEADING_PADDING)

    x = -FRAME_HEADING_PADDING
    y = -label_size.height - (FRAME_HEADING_PADDING / 2)
    ctx.translate(x, y)

    ctx.set_source_rgb(*BACKGROUND_COLOR)
    rounded_rect(ctx, label_size, FRAME_HEADING_BORDER_RADIUS)
    ctx.fill()

    ctx.set_source_rgb(*TEXT_COLOR)
    show_layout_by_lines(ctx, layout, padding=FRAME_HEADING_PADDING)

    ctx.restore()

    return label_size


def finalize_frame(
    self: TldrawRenderer[Any],
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: FrameShape,
    frame_map: Dict[str, List[BaseShapeProto]],
) -> None:
    print(f"\tTldraw: Finalizing frame shape: {id}")

    ctx.push_group()

    ctx.rotate(shape.rotation)
    dash_frame(self, ctx, shape, frame_map)

    finalize_frame_name(ctx, shape)

    ctx.pop_group_to_source()
    ctx.paint_with_alpha(shape.style.opacity)
