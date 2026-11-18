from typing import List, Tuple

import cairo
import pytest

from bbb_presentation_video.renderer.tldraw.shape.text import create_pango_layout
from bbb_presentation_video.renderer.tldraw.utils import AlignStyle, Style

LEFT_TO_RIGHT = "Longer first line\nShort"
RIGHT_TO_LEFT = "שורה ראשונה ארוכה\nקצר"


def line_edges(text: str, align: AlignStyle) -> List[Tuple[float, float]]:
    """The left and right edge of every line, as fractions of the layout width."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    layout = create_pango_layout(ctx, Style(), "Arial", 20, width=600, align=align)
    layout.set_text(text, -1)
    width = layout.get_width()
    edges = []
    lines = layout.get_iter()
    while True:
        _, logical = lines.get_line_extents()
        edges.append((logical.x / width, (logical.x + logical.width) / width))
        if not lines.next_line():
            return edges


@pytest.mark.parametrize("text", [LEFT_TO_RIGHT, RIGHT_TO_LEFT])
def test_alignment_does_not_follow_the_text_direction(text: str) -> None:
    # The client aligns with CSS text-align left, center and right, which are
    # the same sides of the box for right-to-left text
    for left, right in line_edges(text, AlignStyle.START):
        assert left == 0
        assert right < 1
    for left, right in line_edges(text, AlignStyle.MIDDLE):
        assert left > 0
        assert left + right == pytest.approx(1)
    for left, right in line_edges(text, AlignStyle.END):
        assert left > 0
        assert right == pytest.approx(1)


def test_right_to_left_text_is_still_laid_out_right_to_left() -> None:
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    layout = create_pango_layout(ctx, Style(), "Arial", 20, align=AlignStyle.START)
    layout.set_text("אב", -1)
    # The first letter of the text is the one drawn further right
    first = layout.index_to_pos(0)
    second = layout.index_to_pos(len("א".encode()))
    assert first.x > second.x
