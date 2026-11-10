# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.renderer.tldraw.shape import StickyShapeV2
from bbb_presentation_video.renderer.tldraw.utils import (
    BoxShadow,
    ColorStyle,
    rounded_rect,
    rounded_rect_shadow,
)
from bbb_presentation_video.renderer.tldraw.v2.shape.text import finalize_sticky_text
from bbb_presentation_video.renderer.tldraw.v2.utils import COLORS, NOTE_BORDER_RADIUS

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)

# .tl-note__container box-shadow: var(--shadow-1)
NOTE_SHADOW = (BoxShadow(0, 1, 2, 0.25), BoxShadow(0, 1, 3, 0.09))


def finalize_sticky(ctx: cairo.Context[CairoSomeSurface], shape: StickyShapeV2) -> None:
    style = shape.style

    if style.color is ColorStyle.BLACK:
        style.color = ColorStyle.YELLOW

    ctx.rotate(shape.rotation)

    ctx.push_group()

    rounded_rect_shadow(ctx, shape.size, NOTE_BORDER_RADIUS, NOTE_SHADOW)

    # And fill with sticky note background color
    rounded_rect(ctx, shape.size, NOTE_BORDER_RADIUS)
    ctx.set_source_rgb(*COLORS[style.color])
    ctx.fill()

    finalize_sticky_text(ctx, shape)

    ctx.pop_group_to_source()
    ctx.paint_with_alpha(style.opacity)
