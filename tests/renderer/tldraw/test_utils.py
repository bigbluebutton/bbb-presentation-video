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


def test_blurred_shadow_fades_in_steps() -> None:
    # box-shadow: 0px 0px 4px rgba(0, 0, 0, 0.2)
    alphas = shadow_alphas([BoxShadow(0, 0, 4, 0.2)])
    row = alphas[30]
    # Walking in from the left, the four layers start 3px and 1px outside and
    # inside the edge of the box at x=20, each a quarter of the alpha darker
    assert row[14:25] == pytest.approx(
        [0, 0, 0, 0.05, 0.05, 0.1, 0.1, 0.15, 0.15, 0.2, 0.2], abs=0.01
    )
    # The same on every side
    assert row == pytest.approx(row[::-1], abs=0.01)
    assert [alphas[y][30] for y in range(60)] == pytest.approx(row, abs=0.01)


def test_shadow_is_moved_by_its_offset() -> None:
    # box-shadow: 0px 2px 0px rgba(0, 0, 0, 0.5): a hard shadow two pixels down
    alphas = shadow_alphas([BoxShadow(0, 2, 0, 0.5)])
    assert alphas[41][30] == pytest.approx(0.5, abs=0.01)
    assert alphas[21][30] == 0
    assert alphas[30][19] == 0


def test_shadows_stack() -> None:
    # Two shadows darken each other where they overlap, and each keeps its own reach
    alphas = shadow_alphas([BoxShadow(0, 0, 0, 0.3), BoxShadow(0, 0, 4, 0.2)])
    assert alphas[30][30] == pytest.approx(1 - 0.7 * 0.8, abs=0.02)
    assert alphas[30][18] == pytest.approx(0.05, abs=0.01)
    assert alphas[30][16] == 0
