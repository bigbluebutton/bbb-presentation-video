# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Optional, TypeVar

import cairo
import gi

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.renderer.tldraw.shape import (
    FrameShape,
    LabelledShapeProto,
    StickyShape_v2,
    TextShape_v2,
)
from bbb_presentation_video.renderer.tldraw.shape.text import (
    create_pango_layout,
    get_layout_size,
    show_layout_by_lines,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    FONT_SIZES,
    STICKY_FONT_SIZES,
    STICKY_PADDING,
    STICKY_TEXT_COLOR,
    STROKES,
    AlignStyle,
    ColorStyle,
    FontStyle,
    SizeStyle,
)

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

# Set DPI to "72" so we're working directly in Pango point units.
DPI: float = 72.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def finalize_v2_text(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TextShape_v2
) -> None:
    print(f"\tTldraw: Finalizing Text (v2): {id}")

    style = shape.style
    ctx.rotate(shape.rotation)

    stroke = STROKES[style.color]
    font_size = FONT_SIZES[style.size]

    layout = create_pango_layout(ctx, style, font_size)
    layout.set_text(shape.text, -1)

    border_thickness = 2
    border_color = (1, 1, 1, 1)  # White
    # Draw the border by offsetting the text in several directions
    offsets = [
        (-border_thickness, -border_thickness),
        (border_thickness, -border_thickness),
        (-border_thickness, border_thickness),
        (border_thickness, border_thickness),
    ]

    for dx, dy in offsets:
        ctx.translate(dx, dy)
        ctx.set_source_rgba(*border_color)
        show_layout_by_lines(ctx, layout, padding=4)
        ctx.translate(-dx, -dy)  # Reset translation for next iteration

    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)
    show_layout_by_lines(ctx, layout, padding=4)


def finalize_v2_label(
    ctx: cairo.Context[CairoSomeSurface],
    shape: LabelledShapeProto,
    *,
    offset: Optional[Position] = None,
) -> Size:
    if shape.label is None or shape.label == "":
        return Size(16, 32)

    print(f"\t\tFinalizing Label (v2)")

    style = shape.style
    stroke = STROKES[ColorStyle.BLACK]  # v2 labels are always black
    border_color = (1, 1, 1, 1)  # White
    font_size = FONT_SIZES[style.size]

    ctx.save()

    # Create layout aligning the text horizontally within the shape
    style.textAlign = shape.align
    layout = create_pango_layout(
        ctx, style, font_size, width=shape.size.width, padding=4
    )
    layout.set_text(shape.label, -1)

    label_size = get_layout_size(layout, padding=4)
    bounds = shape.size

    if offset is None:
        offset = shape.label_offset()

    x = offset.x

    # Align text vertically in the shape
    if shape.verticalAlign == AlignStyle.START:
        y = offset.y
    elif shape.verticalAlign == AlignStyle.END:
        y = bounds.height - label_size.height + offset.y
    else:
        y = bounds.height / 2 - label_size.height / 2 + offset.y

    border_thickness = 2

    # Draw the border by offsetting the text in several directions
    offsets = [
        (-border_thickness, -border_thickness),
        (border_thickness, -border_thickness),
        (-border_thickness, border_thickness),
        (border_thickness, border_thickness),
    ]

    for dx, dy in offsets:
        ctx.translate(x + dx, y + dy)
        ctx.set_source_rgba(*border_color)
        show_layout_by_lines(ctx, layout, padding=4)
        ctx.translate(-x - dx, -y - dy)  # Reset translation for next iteration

    # Draw the original text on top
    ctx.translate(x, y)
    ctx.set_source_rgba(
        stroke.r, stroke.g, stroke.b, style.opacity
    )  # Set original text color
    show_layout_by_lines(ctx, layout, padding=4)

    ctx.restore()

    return label_size


def finalize_frame_name(
    ctx: cairo.Context[CairoSomeSurface],
    shape: FrameShape,
) -> Size:
    if shape.label is None or shape.label == "":
        return Size(0, 0)

    print(f"\t\tFinalizing Frame name")

    style = shape.style
    stroke = STROKES[ColorStyle.BLACK]
    font_size = 15

    ctx.save()

    # Create layout aligning the text to the top left
    style.textAlign = AlignStyle.START
    style.font = FontStyle.ARIAL
    layout = create_pango_layout(
        ctx,
        style,
        font_size,
        width=shape.size.width,
        padding=0,
    )

    layout.set_text(shape.label, -1)

    label_size = get_layout_size(layout, padding=4)

    x = 0
    y = -20
    ctx.translate(x, y)
    ctx.set_source_rgba(stroke.r, stroke.g, stroke.b, style.opacity)

    show_layout_by_lines(ctx, layout, padding=4)

    ctx.restore()

    return label_size


def finalize_sticky_text_v2(
    ctx: cairo.Context[CairoSomeSurface], shape: StickyShape_v2
) -> None:
    if shape.text is None or shape.text == "":
        return

    print(f"\t\tFinalizing Sticky Text (v2)")

    style = shape.style

    # Horizontal alignment
    style.textAlign = shape.align
    font_size = STICKY_FONT_SIZES[style.size]

    layout = create_pango_layout(
        ctx, style, font_size, width=shape.size.width, padding=STICKY_PADDING
    )
    layout.set_text(shape.text, -1)

    # Calculate vertical position to center the text
    _, text_height = get_layout_size(layout, padding=STICKY_PADDING)
    x, y = ctx.get_current_point()

    if shape.verticalAlign is AlignStyle.MIDDLE:
        y = (shape.size.height - text_height) / 2
    elif shape.verticalAlign is AlignStyle.END:
        y = shape.size.height - text_height
    ctx.translate(x, y)

    ctx.set_source_rgba(
        STICKY_TEXT_COLOR.r, STICKY_TEXT_COLOR.g, STICKY_TEXT_COLOR.b, style.opacity
    )
    show_layout_by_lines(ctx, layout, padding=STICKY_PADDING)
