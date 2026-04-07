# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Optional, TypeVar

import attr
import cairo

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.shape.proto import (
    LabelledShapeProto,
    RotatableShapeProto,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    AlignStyle,
    ColorStyle,
    create_pango_layout,
    get_layout_size,
    show_layout_by_lines,
)
from bbb_presentation_video.renderer.tldraw.v2.utils import (
    BACKGROUND_COLOR,
    COLORS,
    FONT_FAMILIES,
    FONT_SIZES,
    LABEL_FONT_SIZES,
    LINE_HEIGHT,
)

TEXT_OUTLINE_WIDTH: float = 1.0
LABEL_PADDING: float = 16.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShapeV2(RotatableShapeProto):
    text: str = ""

    align: AlignStyle = AlignStyle.MIDDLE
    """Horizontal alignment of the label."""

    auto_size: bool = False

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            props = data["props"]
            if "text" in props:
                self.text = props["text"]
            if "align" in props:
                self.align = AlignStyle(props["align"])
            if "autoSize" in props:
                self.auto_size = props["autoSize"]


def finalize_text(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TextShapeV2
) -> None:
    print(f"\tTldraw: Finalizing Text (v2): {id}")

    style = shape.style

    ctx.rotate(shape.rotation)

    # A group is used so the text border and fill can be drawn opaque (to avoid over-draw issues), then
    # be blended with alpha afterwards
    ctx.push_group()

    width = None
    wrap = False
    if not shape.auto_size:
        wrap = True
        if shape.size.width > 0:
            width = shape.size.width

    layout = create_pango_layout(
        ctx,
        style,
        FONT_FAMILIES[style.font],
        FONT_SIZES[style.size],
        width=width,
        align=shape.align,
        wrap=wrap,
        letter_spacing=None,
    )
    layout.set_text(shape.text, -1)

    # Draw text border (outside stroke)
    ctx.save()
    ctx.set_source_rgb(*BACKGROUND_COLOR)
    ctx.set_line_width(TEXT_OUTLINE_WIDTH * 2)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    show_layout_by_lines(ctx, layout, padding=4, do_path=True, line_height=LINE_HEIGHT)
    ctx.stroke()
    ctx.restore()

    # Draw text
    ctx.set_source_rgb(*COLORS[style.color])
    show_layout_by_lines(ctx, layout, padding=4, line_height=LINE_HEIGHT)

    # Composite result with opacity applied
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(style.opacity)


def finalize_label(
    ctx: cairo.Context[CairoSomeSurface],
    shape: LabelledShapeProto,
    *,
    offset: Optional[Position] = None,
) -> Size:
    if shape.label is None or shape.label == "":
        return Size(16, 32)

    print(f"\t\tFinalizing Label (v2)")

    style = shape.style

    ctx.save()

    width = shape.size.width if shape.size.width > 0 else None
    layout = create_pango_layout(
        ctx,
        style,
        FONT_FAMILIES[style.font],
        LABEL_FONT_SIZES[style.size],
        width=width,
        padding=LABEL_PADDING,
        align=shape.align,
        letter_spacing=None,
    )
    layout.set_text(shape.label, -1)

    label_size = get_layout_size(layout, padding=LABEL_PADDING, line_height=LINE_HEIGHT)
    bounds = shape.size

    if offset is None:
        offset = shape.label_offset()

    x = offset.x + LABEL_PADDING

    # Align text vertically in the shape
    if shape.verticalAlign == AlignStyle.START:
        y = offset.y + LABEL_PADDING
    elif shape.verticalAlign == AlignStyle.END:
        y = bounds.height - label_size.height + offset.y + LABEL_PADDING
    else:
        y = bounds.height / 2 - label_size.height / 2 + offset.y + LABEL_PADDING

    ctx.translate(x, y)

    # Draw text border (outside stroke)
    ctx.save()
    ctx.set_source_rgb(*BACKGROUND_COLOR)
    ctx.set_line_width(TEXT_OUTLINE_WIDTH * 2)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    show_layout_by_lines(ctx, layout, padding=4, do_path=True, line_height=LINE_HEIGHT)
    ctx.stroke()
    ctx.restore()

    # Draw the original text on top
    ctx.set_source_rgb(*COLORS[ColorStyle.BLACK])
    show_layout_by_lines(ctx, layout, padding=4, line_height=LINE_HEIGHT)

    ctx.restore()

    return label_size
