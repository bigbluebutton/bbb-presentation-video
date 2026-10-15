from bbb_presentation_video.renderer.tldraw.shape.poll import (
    chart_height_under_question,
    truncate_label,
)


def test_truncate_label() -> None:
    # An 80px axis and a 5.56px character leave room for 13 characters
    assert truncate_label("True", 80, 5.56) == "True"
    assert truncate_label("Thirteen char", 80, 5.56) == "Thirteen char"
    assert truncate_label("Fourteen chars", 80, 5.56) == "Fourteen c..."
    assert truncate_label("Anything", 8, 5.56) == "..."


def test_chart_height_under_question() -> None:
    # The chart gets what the question and its 8px margins leave, so a long
    # question shrinks the chart instead of pushing its last bars out
    assert chart_height_under_question(300, 24) == 300 - 8 - 24 - 8
    assert chart_height_under_question(550, 175) == 550 - 8 - 175 - 8
