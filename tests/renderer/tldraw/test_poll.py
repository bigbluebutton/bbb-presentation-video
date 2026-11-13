from typing import Callable

import cairo
import pytest

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import PollShape, PollShapeAnswer
from bbb_presentation_video.renderer.tldraw.shape.poll import (
    BORDER_WIDTH,
    CHART_MARGIN,
    finalize_poll,
)


def typed_poll() -> PollShape:
    """A typed poll with an answer far longer than the label column."""
    shape = PollShape()
    shape.size = Size(300, 200)
    shape.questionType = "R-"
    shape.questionText = "What is the question?"
    shape.answers = [
        PollShapeAnswer(key="A" * 200, numVotes=3, isCorrectAnswer=False),
        PollShapeAnswer(key="Short", numVotes=1, isCorrectAnswer=False),
    ]
    return shape


def render(shape: PollShape) -> Callable[[int, int], bytes]:
    """Draw the poll on a transparent surface; returns a reader for its BGRA pixels."""
    surface = cairo.ImageSurface(
        cairo.FORMAT_ARGB32, int(shape.size.width), int(shape.size.height)
    )
    finalize_poll(cairo.Context(surface), "shape:poll", shape)
    surface.flush()
    data = surface.get_data()
    stride = surface.get_stride()

    def pixel(x: int, y: int) -> bytes:
        return bytes(data[y * stride + x * 4 : y * stride + x * 4 + 4])

    return pixel


def test_long_labels_stay_in_the_label_column() -> None:
    # The long answer is ellipsized by Pango instead of running out of the box
    # or over the border
    shape = typed_poll()
    width, height = int(shape.size.width), int(shape.size.height)
    pixel = render(shape)

    # The strip between the border and the chart margin holds nothing but the
    # box background, in every row between the rounded corners
    x = int(BORDER_WIDTH) + 1
    assert x < CHART_MARGIN
    rows = range(10, height - 10)
    background = pixel(x, rows[0])
    assert all(pixel(x, y) == background for y in rows)
    # ...while the label column, which spans half of a typed poll, does get text
    assert any(
        pixel(x, y) != background
        for x in range(int(CHART_MARGIN), width // 2 - 10)
        for y in rows
    )


def test_opacity_fades_the_whole_shape() -> None:
    shape = typed_poll()
    x, y = int(BORDER_WIDTH) + 1, int(shape.size.height) // 2
    # The box is filled with a solid colour...
    assert render(shape)(x, y)[3] == 255
    # ...so with an opacity its alpha is the opacity of the shape
    shape.style.opacity = 0.5
    assert render(shape)(x, y)[3] == pytest.approx(128, abs=1)
