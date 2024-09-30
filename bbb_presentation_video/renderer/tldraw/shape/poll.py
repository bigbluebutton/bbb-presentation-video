# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo

from bbb_presentation_video.renderer.tldraw.shape import PollShape, apply_shape_rotation

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def finalize_poll(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: PollShape
) -> None:
    print(f"\tTldraw: Finalizing Poll: {id}")

    apply_shape_rotation(ctx, shape)
