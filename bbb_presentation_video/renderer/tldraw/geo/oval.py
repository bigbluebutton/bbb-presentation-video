# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from math import cos, sin, tau
from typing import List, TypeVar

import cairo

from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw.shape import Oval
from bbb_presentation_video.renderer.tldraw.shape.text_v2 import finalize_v2_label
from bbb_presentation_video.renderer.tldraw.utils import finalize_geo_path

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def oval_points(w: float, h: float, n_vertices: int = 25) -> List[Position]:
    cx = w / 2
    cy = h / 2

    points: List[Position] = [Position(0, 0)] * (n_vertices * 2 - 2)

    if h > w:
        for i in range(n_vertices - 1):
            t1 = -(tau / 2) + ((tau / 2) * i) / (n_vertices - 2)
            t2 = ((tau / 2) * i) / (n_vertices - 2)
            points[i] = Position(cx + cx * cos(t1), cx + cx * sin(t1))
            points[i + (n_vertices - 1)] = Position(
                cx + cx * cos(t2), h - cx + cx * sin(t2)
            )
    else:
        for i in range(n_vertices - 1):
            t1 = -(tau / 4) + (tau / 2 * i) / (n_vertices - 2)
            t2 = (tau / 4) + (tau / 2 * -i) / (n_vertices - 2)
            points[i] = Position(w - cy + cy * cos(t1), h - cy + cy * sin(t1))
            points[i + (n_vertices - 1)] = Position(
                cy - cy * cos(t2), h - cy + cy * sin(t2)
            )

    return points


def dash_oval(ctx: cairo.Context[CairoSomeSurface], shape: Oval) -> None:
    style = shape.style

    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    n_vertices = 50
    points = oval_points(w, h, n_vertices)

    finalize_geo_path(ctx, points, style)


def finalize_oval(ctx: cairo.Context[CairoSomeSurface], id: str, shape: Oval) -> None:
    print(f"\tTldraw: Finalizing Oval: {id}")

    ctx.rotate(shape.rotation)

    dash_oval(ctx, shape)

    finalize_v2_label(ctx, shape)
