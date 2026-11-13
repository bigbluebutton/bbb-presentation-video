from math import pi
from typing import List, Tuple

import cairo
import pytest

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import PollShape, PollShapeAnswer
from bbb_presentation_video.renderer.tldraw.shape.poll import (
    BAR_COLOR,
    BORDER_WIDTH,
    CHART_MARGIN,
    TICK_MARGIN,
    TICK_SIZE,
    TITLE_FONT_SIZE,
    finalize_poll,
    text_layout,
)

# A bar as it is stored in a cairo ARGB32 surface
BAR = bytes(round(c * 255) for c in (BAR_COLOR.b, BAR_COLOR.g, BAR_COLOR.r, 1))


def poll(
    question: str, question_type: str, answers: List[Tuple[str, int]]
) -> PollShape:
    shape = PollShape()
    shape.size = Size(300, 200)
    shape.questionType = question_type
    shape.questionText = question
    shape.answers = [
        PollShapeAnswer(key=key, numVotes=votes, isCorrectAnswer=False)
        for key, votes in answers
    ]
    return shape


class Rendering:
    """A poll drawn on a transparent surface, with its origin at the given pixel."""

    def __init__(
        self,
        shape: PollShape,
        origin: Tuple[int, int] = (0, 0),
        size: Tuple[int, int] = (300, 200),
    ) -> None:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *size)
        ctx = cairo.Context(surface)
        ctx.translate(*origin)
        finalize_poll(ctx, "shape:poll", shape)
        surface.flush()
        self.data = bytes(surface.get_data())
        self.stride = surface.get_stride()
        self.origin = origin

    def pixel(self, x: int, y: int) -> bytes:
        """The BGRA bytes of a pixel, in the coordinates of the shape."""
        offset = (y + self.origin[1]) * self.stride + (x + self.origin[0]) * 4
        return self.data[offset : offset + 4]


def test_chart_geometry() -> None:
    # Without a question the chart starts 9px down (the border and the margin
    # of the empty title) and takes the height of the shape. recharts gives it
    # 90% of the width, keeps 5px free on every side, 80px for the labels and
    # 30px for the axis: the bars are drawn in x 85..265, y 14..174.
    rendering = Rendering(poll("", "TF", [("True", 2), ("False", 3)]))

    def bar_columns(y: int) -> List[int]:
        return [x for x in range(300) if rendering.pixel(x, y) == BAR]

    def bar_rows(x: int) -> List[int]:
        return [y for y in range(200) if rendering.pixel(x, y) == BAR]

    # Each answer gets a band of 80px, and its bar the middle 80% of it
    assert bar_rows(100) == [*range(22, 86), *range(102, 166)]
    # The ticks are 0 to 4: 2 votes reach half of the 180px, 3 votes three quarters
    assert bar_columns(54) == [*range(85, 175)]
    assert bar_columns(134) == [*range(85, 220)]


def test_long_labels_stay_in_the_label_column() -> None:
    # A typed answer far longer than the label column is ellipsized by Pango
    # instead of running out of the box or over the border
    rendering = Rendering(poll("", "R-", [("A" * 200, 3), ("Short", 1)]))

    # The strip between the border and the chart margin holds nothing but the
    # box background, in every row between the rounded corners
    x = int(BORDER_WIDTH) + 1
    assert x < CHART_MARGIN
    rows = range(10, 190)
    background = rendering.pixel(x, rows[0])
    assert all(rendering.pixel(x, y) == background for y in rows)
    # ...while the label column, which spans half of a typed poll, does get text
    assert any(
        rendering.pixel(x, y) != background
        for x in range(int(CHART_MARGIN), 140)
        for y in rows
    )


def test_right_to_left_labels_end_at_their_tick() -> None:
    rendering = Rendering(poll("", "R-", [("אב", 1)]))
    background = rendering.pixel(int(BORDER_WIDTH) + 1, 100)

    def has_text(columns: range) -> bool:
        return any(
            rendering.pixel(x, y) != background for x in columns for y in range(10, 190)
        )

    # The label column of a typed poll spans half of the shape; a short label
    # sits at the end of it, next to its tick, and not at the start
    label_end = 150 + int(CHART_MARGIN - TICK_SIZE - TICK_MARGIN)
    assert has_text(range(label_end - 20, label_end))
    assert not has_text(range(int(CHART_MARGIN), 75))


def test_question_white_space_is_collapsed() -> None:
    # Like HTML does: the client shows a question typed on several lines as
    # running text
    answers = [("True", 2), ("False", 3)]
    typed = Rendering(poll(" Which one\nis it?\t\tThis\r\n  one? ", "TF", answers))
    collapsed = Rendering(poll("Which one is it? This one?", "TF", answers))
    assert typed.data == collapsed.data


def test_text_measures_the_same_at_every_scale() -> None:
    # Shapes are drawn again whenever the zoom changes, and the question must
    # not wrap differently when they are
    widths = []
    for scale in (0.5, 1.0, 1.1, 1.25, 1.5, 2.0, 3.0):
        ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
        ctx.scale(scale, scale)
        layout = text_layout(ctx, TITLE_FONT_SIZE)
        layout.set_text("What is the capital of France?", -1)
        widths.append(layout.get_size()[0])
    # In Pango units, 1024 to the pixel
    assert max(widths) - min(widths) < 1024


def test_rotation_is_around_the_shape_origin() -> None:
    # tldraw 2 rotates a shape around its origin, the top left corner: turned
    # a quarter clockwise, the 300x200 box covers x -200..0, y 0..300
    shape = poll("", "TF", [("True", 2), ("False", 3)])
    shape.rotation = pi / 2
    rendering = Rendering(shape, origin=(220, 10), size=(560, 330))
    assert rendering.pixel(-100, 150)[3] == 255
    assert rendering.pixel(-190, 290)[3] == 255
    # ...and none of the area it would cover if turned around its center
    assert rendering.pixel(100, 100)[3] == 0
    assert rendering.pixel(240, 100)[3] == 0


def test_opacity_fades_the_whole_shape() -> None:
    shape = poll("Which one is it?", "R-", [("One", 3), ("Other", 1)])
    # A column through the question, both bars and the axis
    column = [(160, y) for y in range(2, 198)]
    opaque = Rendering(shape)
    assert all(opaque.pixel(x, y)[3] == 255 for x, y in column)
    shape.style.opacity = 0.5
    faded = Rendering(shape)
    assert [faded.pixel(x, y)[3] for x, y in column] == pytest.approx(
        [128] * len(column), abs=1
    )
