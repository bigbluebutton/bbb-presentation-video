from math import erfc, sqrt
from typing import List, Sequence

import cairo
import pytest

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.utils import BoxShadow, rounded_rect_shadow


def shadow_alphas(shadows: Sequence[BoxShadow]) -> List[List[float]]:
    """Alpha of every pixel after drawing the shadow of a 20x20 box at (20, 20)."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 60, 60)
    ctx = cairo.Context(surface)
    ctx.translate(20, 20)
    rounded_rect_shadow(ctx, Size(20, 20), 2, shadows)
    surface.flush()
    data = surface.get_data()
    stride = surface.get_stride()
    return [[data[y * stride + x * 4 + 3] / 255 for x in range(60)] for y in range(60)]


def gaussian_edge(alpha: float, blur: float, distance: float) -> float:
    """Alpha of a CSS box-shadow at a distance outside the edge of its box."""
    return alpha * erfc(distance / (blur / 2 * sqrt(2))) / 2


def test_blurred_shadow_fades_like_a_gaussian() -> None:
    # box-shadow: 0px 0px 4px rgba(0, 0, 0, 0.2)
    alphas = shadow_alphas([BoxShadow(0, 0, 4, 0.2)])
    row = alphas[30]
    # Solid under the box, nothing past the blur radius
    assert row[30] == pytest.approx(0.2, abs=0.01)
    assert row[15] == 0
    assert row[44] == 0
    # The pixels across the edge carry the Gaussian sampled at their centers
    expected = [gaussian_edge(0.2, 4, d) for d in (3.5, 2.5, 1.5, 0.5, -0.5)]
    assert row[16:21] == pytest.approx(expected, abs=0.01)
    # Symmetric on every side
    assert row[15:20] == pytest.approx(list(reversed(row[40:45])), abs=0.01)
    column = [alphas[y][30] for y in range(60)]
    assert column == pytest.approx(row, abs=0.01)


def test_flat_shadow_is_moved_by_its_offset() -> None:
    # box-shadow: 0px 2px 0px rgba(0, 0, 0, 0.5): a hard shadow two pixels down
    alphas = shadow_alphas([BoxShadow(0, 2, 0, 0.5)])
    assert alphas[41][30] == pytest.approx(0.5, abs=0.01)
    assert alphas[21][30] == 0
    assert alphas[30][19] == 0


def test_shadow_layers_stack() -> None:
    # Two layers darken each other where they overlap, and each keeps its own reach
    alphas = shadow_alphas([BoxShadow(0, 0, 0, 0.3), BoxShadow(0, 0, 4, 0.2)])
    assert alphas[30][30] == pytest.approx(1 - 0.7 * 0.8, abs=0.01)
    assert alphas[30][19] == pytest.approx(gaussian_edge(0.2, 4, 0.5), abs=0.01)
    assert alphas[30][15] == 0
