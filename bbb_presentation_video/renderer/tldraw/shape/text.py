# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import TypeVar

import cairo
import gi

from bbb_presentation_video.renderer.tldraw.shape import (
    LabelledShapeProto,
    TextShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    FONT_FACES,
    FONT_SIZES,
    STROKES,
    AlignStyle,
    Style,
)

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo


def set_pango_font(pctx: Pango.Context, style: Style) -> Pango.FontDescription:
    font = Pango.FontDescription()
    font.set_family(FONT_FACES[style.font])
    font.set_absolute_size(FONT_SIZES[style.size] * style.scale * Pango.SCALE)

    fo = cairo.FontOptions()
    fo.set_antialias(cairo.ANTIALIAS_GRAY)
    fo.set_hint_metrics(cairo.HINT_METRICS_ON)
    fo.set_hint_style(cairo.HINT_STYLE_NONE)
    PangoCairo.context_set_font_options(pctx, fo)

    return font


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def finalize_text(
    ctx: "cairo.Context[CairoSomeSurface]", id: str, shape: TextShape
) -> None:
    print(f"\tTldraw: Finalizing Text: {id}")

    apply_shape_rotation(ctx, shape)

    style = shape.style

    pctx = PangoCairo.create_context(ctx)
    font = set_pango_font(pctx, style)

    layout = Pango.Layout(pctx)
    layout.set_auto_dir(True)
    layout.set_font_description(font)
    if shape.size.width > 0:
        layout.set_width(int(shape.size.width * Pango.SCALE))
    if shape.size.height > 0:
        layout.set_height(int(shape.size.height * Pango.SCALE))
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    if style.textAlign == AlignStyle.START:
        layout.set_alignment(Pango.Alignment.LEFT)
    elif style.textAlign == AlignStyle.MIDDLE:
        layout.set_alignment(Pango.Alignment.CENTER)
    elif style.textAlign == AlignStyle.END:
        layout.set_alignment(Pango.Alignment.RIGHT)
    elif style.textAlign == AlignStyle.JUSTIFY:
        layout.set_alignment(Pango.Alignment.LEFT)
        layout.set_justify(True)

    layout.set_text(shape.text, -1)

    ctx.set_source_rgb(*STROKES[style.color])

    PangoCairo.show_layout(ctx, layout)


def finalize_label(
    ctx: "cairo.Context[CairoSomeSurface]", shape: LabelledShapeProto
) -> None:
    if shape.label is None or shape.label == "":
        return

    print(f"\tTldraw: Finalizing Label")

    style = shape.style

    pctx = PangoCairo.create_context(ctx)
    font = set_pango_font(pctx, style)

    layout = Pango.Layout(pctx)
    layout.set_auto_dir(True)
    layout.set_font_description(font)
    if shape.size.width > 0:
        layout.set_width(int(shape.size.width * Pango.SCALE))
    if shape.size.height > 0:
        layout.set_height(int(shape.size.height * Pango.SCALE))
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_alignment(Pango.Alignment.CENTER)

    layout.set_text(shape.label, -1)

    (_, layout_height) = layout.get_pixel_size()
    height_offset = (shape.size.height - layout_height) / 2
    ctx.translate(0, height_offset)

    ctx.set_source_rgb(*STROKES[style.color])

    PangoCairo.show_layout(ctx, layout)
