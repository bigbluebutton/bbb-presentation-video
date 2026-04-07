# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import StickyShapeV2
from bbb_presentation_video.renderer.tldraw.utils import (
    ColorStyle,
    rounded_rect,
)
from bbb_presentation_video.renderer.tldraw.v2.shape.text import finalize_sticky_text
from bbb_presentation_video.renderer.tldraw.v2.utils import COLORS, NOTE_BORDER_RADIUS

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


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
