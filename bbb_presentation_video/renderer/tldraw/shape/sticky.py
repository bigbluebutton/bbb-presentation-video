# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import attr
import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.shape.proto import RotatableShapeProto
from bbb_presentation_video.renderer.tldraw.utils import (
    FONT_FACES,
    STICKY_FILLS,
    STICKY_FONT_SIZES,
    STICKY_PADDING,
    STICKY_TEXT_COLOR,
    ColorStyle,
    create_pango_layout,
    rounded_rect,
    show_layout_by_lines,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(order=False, slots=True, auto_attribs=True)
class StickyShape(RotatableShapeProto):
    text: str = ""

    # SizedShapeProto
    size: Size = Size(200.0, 200.0)

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]


def finalize_sticky_text(
    ctx: cairo.Context[CairoSomeSurface], shape: StickyShape
) -> None:
    if shape.text is None or shape.text == "":
        return

    print(f"\t\tFinalizing Sticky Text")

    style = shape.style
    font_description = FONT_FACES[style.font]
    font_size = STICKY_FONT_SIZES[style.size]

    layout = create_pango_layout(
        ctx,
        style,
        font_description,
        font_size,
        width=shape.size.width,
        padding=STICKY_PADDING,
    )
    layout.set_text(shape.text, -1)

    ctx.set_source_rgb(STICKY_TEXT_COLOR.r, STICKY_TEXT_COLOR.g, STICKY_TEXT_COLOR.b)
    show_layout_by_lines(ctx, layout, padding=STICKY_PADDING)


def finalize_sticky(ctx: cairo.Context[CairoSomeSurface], shape: StickyShape) -> None:
    shape.apply_shape_rotation(ctx)

    style = shape.style
    if style.color is ColorStyle.WHITE or style.color is ColorStyle.BLACK:
        style.color = ColorStyle.YELLOW
    fill = STICKY_FILLS[style.color]

    # Shadow. Doing blurred shadow is hard, so this is a simple offset drop shadow + border instead
    ctx.save()
    ctx.translate(-1.0, -1.0)
    blur_size = Size(shape.size.width + 3, shape.size.height + 3)
    rounded_rect(ctx, blur_size, 5)
    ctx.set_source_rgba(0, 0, 0, 0.15)
    ctx.fill()
    ctx.restore()

    rounded_rect(ctx, shape.size, 3)
    ctx.set_source_rgba(0, 0, 0, 0.15)
    ctx.set_line_width(2.0)
    ctx.stroke_preserve()

    # And fill with sticky note background color
    ctx.set_source_rgb(fill.r, fill.g, fill.b)
    ctx.fill()

    finalize_sticky_text(ctx, shape)
