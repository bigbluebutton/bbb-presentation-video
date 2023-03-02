# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import TypeVar

import cairo
import gi

from bbb_presentation_video.renderer.tldraw import vec
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShape,
    LabelledShapeProto,
    StickyShape,
    TextShape,
    TriangleShape,
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
    DashStyle,
    Style,
    triangle_centroid,
)

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

# Set DPI to "72" so we're working directly in Pango point units.
DPI: float = 72.0


def create_pango_layout(
    pctx: Pango.Context, style: Style, font_size: float
) -> Pango.Layout:
    scale = style.scale

    font = Pango.FontDescription()
    font.set_family(FONT_FACES[style.font])
    font.set_size(round(font_size * scale * Pango.SCALE))

    fo = cairo.FontOptions()
    fo.set_antialias(cairo.ANTIALIAS_GRAY)
    fo.set_hint_metrics(cairo.HINT_METRICS_ON)
    fo.set_hint_style(cairo.HINT_STYLE_NONE)
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

    return layout


def show_layout_by_lines(
    ctx: "cairo.Context[CairoSomeSurface]", layout: Pango.Layout
) -> None:
    # TODO: With Pango 1.50 this can be replaced with Pango.attr_line_height_new_absolute

    font = layout.get_font_description()
    # Assuming CSS "line-height: 1;" - i.e. line height = font size
    line_height = font.get_size() / Pango.SCALE

    ctx.save()
    for line in layout.get_lines_readonly():
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
        ctx.translate(0, offset_y)
        PangoCairo.show_layout_line(ctx, line)
        ctx.restore()
        ctx.translate(0, line_height)
    ctx.restore()


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def finalize_text(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: TextShape
) -> None:
    print(f"\tTldraw: Finalizing Text: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style
    stroke = STROKES[style.color]
    font_size = FONT_SIZES[style.size]

    pctx = PangoCairo.create_context(ctx)
    layout = create_pango_layout(pctx, style, font_size)

    layout.set_text(shape.text, -1)

    ctx.translate(4.0, 4.0)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)
    show_layout_by_lines(ctx, layout)


def finalize_label(
    ctx: "cairo.Context[CairoSomeSurface]", shape: LabelledShapeProto
) -> None:
    if shape.label is None or shape.label == "":
        return

    print(f"\tTldraw: Finalizing Label")

    style = shape.style
    # Label text is always centered
    style.textAlign = AlignStyle.MIDDLE
    stroke = STROKES[style.color]
    font_size = FONT_SIZES[style.size]

    pctx = PangoCairo.create_context(ctx)
    layout = create_pango_layout(pctx, style, font_size)

    layout.set_text(shape.label, -1)

    (layout_width, layout_height) = layout.get_pixel_size()
    if style.dash is DashStyle.DRAW or isinstance(shape, TriangleShape):
        width_offset = (shape.size.width - layout_width) * shape.labelPoint.x
        height_offset = (shape.size.height - layout_height) * shape.labelPoint.y
    else:
        width_offset = (-layout_width) * shape.labelPoint.x
        height_offset = (-layout_height) * shape.labelPoint.y

    if isinstance(shape, TriangleShape):
        # label of triangle has an offset
        center = vec.div([shape.size.width, shape.size.height], 2)
        centroid = triangle_centroid(shape.size.width, shape.size.height)
        offsetY = (centroid[1] - center[1]) * 0.72
        height_offset += offsetY

    ctx.translate(width_offset, height_offset)
    ctx.set_source_rgb(stroke.r, stroke.g, stroke.b)

    show_layout_by_lines(ctx, layout)


def finalize_sticky_text(
    ctx: "cairo.Context[CairoSomeSurface]", shape: StickyShape
) -> None:
    if shape.text is None or shape.text == "":
        return

    print(f"\tTldraw: Finalizing Sticky Text")

    style = shape.style

    font_size = STICKY_FONT_SIZES[style.size]

    pctx = PangoCairo.create_context(ctx)
    layout = create_pango_layout(pctx, style, font_size)
    layout.set_width(int((shape.size.width - (STICKY_PADDING * 2)) * Pango.SCALE))
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)

    layout.set_text(shape.text, -1)

    ctx.translate(STICKY_PADDING, STICKY_PADDING)
    ctx.set_source_rgb(STICKY_TEXT_COLOR.r, STICKY_TEXT_COLOR.g, STICKY_TEXT_COLOR.b)

    show_layout_by_lines(ctx, layout)


def finalize_arrow_label(
    ctx: "cairo.Context[CairoSomeSurface]", shape: ArrowShape
) -> None:
    ...
