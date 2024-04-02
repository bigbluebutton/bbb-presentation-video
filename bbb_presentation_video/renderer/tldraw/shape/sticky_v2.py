# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import StickyShape_v2
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_sticky_text_v2
from bbb_presentation_video.renderer.tldraw.utils import (
    STICKY_FILLS,
    ColorStyle,
    rounded_rect,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def finalize_sticky_v2(
    ctx: cairo.Context[CairoSomeSurface], shape: StickyShape_v2
) -> None:
    style = shape.style

    if style.color is ColorStyle.BLACK:
        style.color = ColorStyle.YELLOW

    fill = STICKY_FILLS[style.color]
    ctx.rotate(shape.rotation)
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
    ctx.set_source_rgba(fill.r, fill.g, fill.b, style.opacity)
    ctx.fill()

    finalize_sticky_text_v2(ctx, shape)
