from bbb_presentation_video.renderer.tldraw.shape import PollShapeAnswer
from bbb_presentation_video.renderer.tldraw.shape.poll import (
    merge_answers,
    truncate_label,
)


def test_merge_answers_is_case_insensitive() -> None:
    answers = [
        PollShapeAnswer(key="Yes", numVotes=1),
        PollShapeAnswer(key="yes", numVotes=2, isCorrectAnswer=True),
        PollShapeAnswer(key="No", numVotes=1),
        PollShapeAnswer(key="NO", numVotes=1),
    ]
    assert merge_answers(answers) == [
        PollShapeAnswer(key="yes", numVotes=3, isCorrectAnswer=True),
        PollShapeAnswer(key="No", numVotes=2),
    ]
    # The input is left untouched
    assert answers[0] == PollShapeAnswer(key="Yes", numVotes=1)


def test_truncate_label() -> None:
    # An 80px axis and a 5.56px character leave room for 13 characters
    assert truncate_label("True", 80, 5.56) == "True"
    assert truncate_label("Thirteen char", 80, 5.56) == "Thirteen char"
    assert truncate_label("Fourteen chars", 80, 5.56) == "Fourteen c..."
    assert truncate_label("Anything", 8, 5.56) == "..."
