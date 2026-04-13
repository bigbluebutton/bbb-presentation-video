# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Callable, Optional, Tuple, TypeVar

import attr
import cairo
import gi
from gi.repository import PangoCairo

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.shape.proto import (
    LabelledShapeProto,
    RotatableShapeProto,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    FONT_FACES,
    FONT_SIZES,
    STROKES,
    AlignStyle,
    create_pango_layout,
    get_layout_size,
    show_layout_by_lines,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShape(RotatableShapeProto):
    text: str = ""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]


def finalize_text(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: TextShape
) -> None:
    print(f"\tTldraw: Finalizing Text: {id}")

    shape.apply_shape_rotation(ctx)

    style = shape.style
    stroke = STROKES[style.color]
    font_description = FONT_FACES[style.font]
    font_size = FONT_SIZES[style.size]

    layout = create_pango_layout(ctx, style, font_description, font_size)
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
    font_description = FONT_FACES[style.font]
    font_size = FONT_SIZES[style.size]

    ctx.save()

    layout = create_pango_layout(ctx, style, font_description, font_size)
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
