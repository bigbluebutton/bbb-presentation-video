# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Dict, Optional, TypeVar

import cairo
import gi

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.renderer.tldraw.shape import (
    FrameShape,
    LabelledShapeProto,
    StickyShapeV2,
    TextShapeV2,
)
from bbb_presentation_video.renderer.tldraw.shape.text import (
    create_pango_layout,
    get_layout_size,
    show_layout_by_lines,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    STICKY_PADDING,
    AlignStyle,
    ColorStyle,
    FontStyle,
    rounded_rect,
)
from bbb_presentation_video.renderer.tldraw.v2.utils import (
    BACKGROUND_COLOR,
    COLORS,
    FONT_FAMILIES,
    FONT_SIZES,
    FRAME_HEADING_BORDER_RADIUS,
    FRAME_HEADING_FONT_SIZE,
    FRAME_HEADING_PADDING,
    LABEL_FONT_SIZES,
    LINE_HEIGHT,
    TEXT_COLOR,
)

TEXT_OUTLINE_WIDTH: float = 1.0
LABEL_PADDING: float = 16.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


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
    if not shape.auto_size and shape.size.width > 0:
        width = shape.size.width

    layout = create_pango_layout(
        ctx,
        style,
        FONT_FAMILIES[style.font],
        FONT_SIZES[style.size],
        width=width,
        align=shape.align,
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


def finalize_sticky_text(
    ctx: cairo.Context[CairoSomeSurface], shape: StickyShapeV2
) -> None:
    if shape.text is None or shape.text == "":
        return

    print(f"\t\tFinalizing Sticky Text (v2)")

    style = shape.style

    layout = create_pango_layout(
        ctx,
        style,
        FONT_FAMILIES[style.font],
        LABEL_FONT_SIZES[style.size],
        width=shape.size.width,
        padding=STICKY_PADDING,
        align=shape.align,
    )
    layout.set_text(shape.text, -1)

    # Calculate vertical position to center the text
    _, text_height = get_layout_size(
        layout, padding=STICKY_PADDING, line_height=LINE_HEIGHT
    )
    x, y = ctx.get_current_point()

    if shape.verticalAlign is AlignStyle.MIDDLE:
        y = (shape.size.height - text_height) / 2
    elif shape.verticalAlign is AlignStyle.END:
        y = shape.size.height - text_height
    ctx.translate(x, y)

    ctx.set_source_rgb(*COLORS[ColorStyle.BLACK])
    show_layout_by_lines(ctx, layout, padding=STICKY_PADDING, line_height=LINE_HEIGHT)
