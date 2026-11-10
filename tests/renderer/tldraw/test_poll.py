import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import PollShape, PollShapeAnswer
from bbb_presentation_video.renderer.tldraw.shape.poll import (
    BORDER_WIDTH,
    CHART_MARGIN,
    finalize_poll,
)


def test_long_labels_stay_in_the_label_column() -> None:
    # A typed answer far longer than the label column is ellipsized by Pango
    # instead of running out of the box or over the border
    shape = PollShape()
    shape.size = Size(300, 200)
    shape.questionType = "R-"
    shape.questionText = "What is the question?"
    shape.answers = [
        PollShapeAnswer(key="A" * 200, numVotes=3, isCorrectAnswer=False),
        PollShapeAnswer(key="Short", numVotes=1, isCorrectAnswer=False),
    ]
    width, height = int(shape.size.width), int(shape.size.height)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    finalize_poll(cairo.Context(surface), "shape:poll", shape)
    surface.flush()
    data = surface.get_data()
    stride = surface.get_stride()

    def pixel(x: int, y: int) -> bytes:
        return bytes(data[y * stride + x * 4 : y * stride + x * 4 + 4])

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
