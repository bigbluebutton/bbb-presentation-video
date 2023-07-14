from __future__ import annotations

from typing import TypeVar

import cairo

BEZIER_CIRCLE_MAGIC = 0.551915024494

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def cairo_draw_ellipse(
    ctx: cairo.Context[CairoSomeSurface], x: float, y: float, rx: float, ry: float
) -> None:
    """Draw a bezier approximation to an ellipse.

    Cairo's arc function can only draw unit circles, and the need to do a transform
    to scale them causes problems when drawing very thin circles. The 4-segment bezier
    approximation to an ellipse is very close, so draw that instead.

    :param x: The x coordinate of the center of the ellipse.
    :param y: The y coordinate of the center of the ellipse.
    :param rx: The horizontal radius of the ellipse.
    :param ry: The vertical radius of the ellipse.
    """
    ctx.save()
    ctx.translate(x, y)
    ctx.move_to(-rx, 0)
    ctx.curve_to(-rx, -ry * BEZIER_CIRCLE_MAGIC, -rx * BEZIER_CIRCLE_MAGIC, -ry, 0, -ry)
    ctx.curve_to(rx * BEZIER_CIRCLE_MAGIC, -ry, rx, -ry * BEZIER_CIRCLE_MAGIC, rx, 0)
    ctx.curve_to(rx, ry * BEZIER_CIRCLE_MAGIC, rx * BEZIER_CIRCLE_MAGIC, ry, 0, ry)
    ctx.curve_to(-rx * BEZIER_CIRCLE_MAGIC, ry, -rx, ry * BEZIER_CIRCLE_MAGIC, -rx, 0)
    ctx.close_path()
    ctx.restore()
