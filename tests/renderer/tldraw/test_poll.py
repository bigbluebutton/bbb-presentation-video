from bbb_presentation_video.renderer.tldraw.shape.poll import truncate_label


def test_truncate_label() -> None:
    # An 80px axis and a 5.56px character leave room for 13 characters
    assert truncate_label("True", 80, 5.56) == "True"
    assert truncate_label("Thirteen char", 80, 5.56) == "Thirteen char"
    assert truncate_label("Fourteen chars", 80, 5.56) == "Fourteen c..."
    assert truncate_label("Anything", 8, 5.56) == "..."
