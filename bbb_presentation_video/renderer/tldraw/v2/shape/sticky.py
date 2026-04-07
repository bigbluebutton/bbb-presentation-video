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
    STICKY_PADDING,
    AlignStyle,
    ColorStyle,
    create_pango_layout,
    get_layout_size,
    rounded_rect,
    show_layout_by_lines,
)
from bbb_presentation_video.renderer.tldraw.v2.utils import (
    COLORS,
    FONT_FAMILIES,
    LABEL_FONT_SIZES,
    LINE_HEIGHT,
    NOTE_BORDER_RADIUS,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(order=False, slots=True, auto_attribs=True)
class StickyShapeV2(RotatableShapeProto):
    text: str = ""
    align: AlignStyle = AlignStyle.MIDDLE
    verticalAlign: AlignStyle = AlignStyle.MIDDLE
    size: Size = Size(200.0, 200.0)

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            props = data["props"]
            if "text" in props:
                self.text = props["text"]
            if "align" in props:
                self.align = AlignStyle(props["align"])
            if "verticalAlign" in props:
                self.verticalAlign = AlignStyle(props["verticalAlign"])
            if "growY" in props:
                self.size = Size(self.size.width, self.size.height + props["growY"])
                if props["growY"] != 0:
                    self.verticalAlign = AlignStyle.START


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


def finalize_sticky(ctx: cairo.Context[CairoSomeSurface], shape: StickyShapeV2) -> None:
    style = shape.style

    if style.color is ColorStyle.BLACK:
        style.color = ColorStyle.YELLOW

    ctx.rotate(shape.rotation)

    ctx.push_group()

    # Shadow. Doing blurred shadow is hard, so this is a two-layer drop shadow instead
    ctx.save()
    ctx.translate(-1.0, 0.0)
    rounded_rect(
        ctx, Size(shape.size.width + 2, shape.size.height + 2), NOTE_BORDER_RADIUS + 1
    )
    ctx.set_source_rgba(0, 0, 0, 0.09)
    ctx.fill()
    ctx.restore()

    ctx.save()
    ctx.translate(0.0, 0.5)
    rounded_rect(ctx, shape.size, NOTE_BORDER_RADIUS)
    ctx.set_source_rgba(0, 0, 0, 0.25)
    ctx.fill()
    ctx.restore()

    # And fill with sticky note background color
    rounded_rect(ctx, shape.size, NOTE_BORDER_RADIUS)
    ctx.set_source_rgb(*COLORS[style.color])
    ctx.fill()

    finalize_sticky_text(ctx, shape)

    ctx.pop_group_to_source()
    ctx.paint_with_alpha(style.opacity)
