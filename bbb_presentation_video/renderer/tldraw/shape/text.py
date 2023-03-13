# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from math import ceil
from typing import Callable, Optional, Tuple, TypeVar

import cairo
import gi

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.renderer.tldraw.shape import (
    LabelledShapeProto,
    StickyShape,
    TextShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    FONT_FACES,
    FONT_SIZES,
    LETTER_SPACING,
    STICKY_FONT_SIZES,
    STICKY_PADDING,
    STICKY_TEXT_COLOR,
    STROKES,
    AlignStyle,
    Style,
)

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

# Set DPI to "72" so we're working directly in Pango point units.
DPI: float = 72.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def create_pango_layout(
    ctx: cairo.Context[CairoSomeSurface],
    style: Style,
    font_size: float,
    *,
    width: Optional[float] = None,
    padding: float = 0,
) -> Pango.Layout:
    scale = style.scale

    pctx = PangoCairo.create_context(ctx)
    pctx.set_round_glyph_positions(False)

    font = Pango.FontDescription()
    font.set_family(FONT_FACES[style.font])
    font.set_size(round(font_size * scale * Pango.SCALE))

    fo = cairo.FontOptions()
    fo.set_antialias(cairo.Antialias.GRAY)
    fo.set_hint_metrics(cairo.HintMetrics.OFF)
    fo.set_hint_style(cairo.HintStyle.NONE)
    PangoCairo.context_set_font_options(pctx, fo)

    attrs = Pango.AttrList()
    letter_spacing_attr = Pango.attr_letter_spacing_new(
        round(LETTER_SPACING * font_size * scale * Pango.SCALE)
    )
    attrs.insert(letter_spacing_attr)
    insert_hyphens_attr = Pango.attr_insert_hyphens_new(insert_hyphens=False)
    attrs.insert(insert_hyphens_attr)

    layout = Pango.Layout(pctx)
    PangoCairo.context_set_resolution(pctx, DPI)
    layout.set_auto_dir(True)
    layout.set_attributes(attrs)
    layout.set_font_description(font)

    if style.textAlign == AlignStyle.START:
        layout.set_alignment(Pango.Alignment.LEFT)
    elif style.textAlign == AlignStyle.MIDDLE:
        layout.set_alignment(Pango.Alignment.CENTER)
    elif style.textAlign == AlignStyle.END:
        layout.set_alignment(Pango.Alignment.RIGHT)
    elif style.textAlign == AlignStyle.JUSTIFY:
        layout.set_alignment(Pango.Alignment.LEFT)
        layout.set_justify(True)

    if width is not None:
        layout.set_width(ceil((width - (padding * 2)) * Pango.SCALE))
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)

    return layout


def show_layout_by_lines(
    ctx: cairo.Context[CairoSomeSurface], layout: Pango.Layout, *, padding: float = 0
) -> None:
    """Show a Pango Layout line by line to manually handle CSS-style line height."""
    # TODO: With Pango 1.50 this can be replaced with Pango.attr_line_height_new_absolute

    font = layout.get_font_description()
    # Assuming CSS "line-height: 1;" - i.e. line height = font size
    line_height = font.get_size() / Pango.SCALE

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
        PangoCairo.show_layout_line(ctx, line)
        ctx.restore()

        ctx.translate(0, line_height)
        if not iter.next_line():
            break

    ctx.restore()


def get_layout_size(layout: Pango.Layout, *, padding: float = 0) -> Size:
    # TODO: Once we switch to Pango 1.50 and use Pango.attr_line_height_new_absolute this can
    # be replaced with a call to layout.get_size()
    layout_size = layout.get_size()
    width = layout_size[0] / Pango.SCALE
    lines = layout.get_line_count()
    font = layout.get_font_description()
    line_height = font.get_size() / Pango.SCALE
    height = lines * line_height
    return Size(width + padding * 2, height + padding * 2)


def finalize_text(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TextShape
) -> None:
    print(f"\tTldraw: Finalizing Text: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style
    stroke = STROKES[style.color]
    font_size = FONT_SIZES[style.size]

    layout = create_pango_layout(ctx, style, font_size)
    layout.set_text(shape.text, -1)

    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    show_layout_by_lines(ctx, layout, padding=4)


def finalize_label(
    ctx: cairo.Context[CairoSomeSurface],
    shape: LabelledShapeProto,
    *,
    offset: Optional[Position] = None,
    scale: Optional[Callable[[Size], float]] = None,
) -> Tuple[Size, float]:
    if shape.label is None or shape.label == "":
        return (Size(16, 32), 1)

    print(f"\t\tFinalizing Label")

    style = shape.style
    # Label text is always centered
    style.textAlign = AlignStyle.MIDDLE
    stroke = STROKES[style.color]
    font_size = FONT_SIZES[style.size]

    ctx.save()

    layout = create_pango_layout(ctx, style, font_size)
    layout.set_text(shape.label, -1)

    label_size = get_layout_size(layout, padding=4)
    # The shape may provide a scale adjustment to reduce label size if it wouldn't fit
    scale_adj = 1.0
    if scale is not None:
        scale_adj = scale(label_size)
        label_size *= scale_adj

    bounds = shape.size
    if offset is None:
        offset = shape.label_offset()
    x = bounds.width / 2 - label_size.width / 2 + offset.x
    y = bounds.height / 2 - label_size.height / 2 + offset.y
    ctx.translate(x, y)

    if scale is not None:
        ctx.scale(scale_adj, scale_adj)
        PangoCairo.update_context(ctx, layout.get_context())
        layout.context_changed()

    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    show_layout_by_lines(ctx, layout, padding=4)

    ctx.restore()

    return (label_size, scale_adj)


def finalize_sticky_text(
    ctx: cairo.Context[CairoSomeSurface], shape: StickyShape
) -> None:
    if shape.text is None or shape.text == "":
        return

    print(f"\t\tFinalizing Sticky Text")

    style = shape.style
    font_size = STICKY_FONT_SIZES[style.size]

    layout = create_pango_layout(
        ctx, style, font_size, width=shape.size.width, padding=STICKY_PADDING
    )
    layout.set_text(shape.text, -1)

    ctx.set_source_rgb(STICKY_TEXT_COLOR.r, STICKY_TEXT_COLOR.g, STICKY_TEXT_COLOR.b)
    show_layout_by_lines(ctx, layout, padding=STICKY_PADDING)
