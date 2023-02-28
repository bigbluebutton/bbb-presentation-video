from pytest import approx

from bbb_presentation_video.events import Size
from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.shape import ArrowShape, DrawShape
from bbb_presentation_video.renderer.tldraw.utils import (
    ColorStyle,
    DashStyle,
    Decoration,
    SizeStyle,
    Style,
)


def test_draw_defaults() -> None:
    draw = DrawShape()
    assert draw.style == Style()
    assert draw.childIndex == 1
    assert draw.point == Position(0, 0)
    assert draw.size == Size(0, 0)
    assert draw.rotation == 0

    assert draw.points == []
    assert draw.isComplete == False


def test_draw_from_data() -> None:
    data: ShapeData = {
        "size": [109.22, 78.48],
        "style": {
            "isFilled": False,
            "size": "small",
            "scale": 1,
            "color": "black",
            "dash": "draw",
        },
        "rotation": 0,
        "type": "draw",
        "isComplete": True,
        "parentId": "1",
        "childIndex": 4.5,
        "name": "Draw",
        "point": [789.92, 460.79],
        "points": [
            [47.85, 0, 0.5],
            [47.85, 0, 0.5],
            [42, 2.99, 0.5],
            [22.44, 19.09, 0.5],
            [7.68, 32.57, 0.5],
            [0, 44.65, 0.5],
            [0, 51.49, 0.5],
            [7.01, 62.36, 0.5],
            [34.65, 70.25, 0.5],
            [68.73, 77.07, 0.5],
            [109.22, 78.48, 0.5],
        ],
        "id": "44b07126-96a9-4935-2b02-cdc0b87620ff",
    }
    draw = DrawShape.from_data(data)
    assert draw.style == Style(
        color=ColorStyle.BLACK,
        size=SizeStyle.SMALL,
        dash=DashStyle.DRAW,
        isFilled=False,
        scale=1,
    )
    assert draw.childIndex == 4.5
    assert draw.point == Position(789.92, 460.79)
    assert draw.size == Size(109.22, 78.48)
    assert draw.rotation == 0

    assert draw.points == [
        (47.85, 0, 0.5),
        (47.85, 0, 0.5),
        (42, 2.99, 0.5),
        (22.44, 19.09, 0.5),
        (7.68, 32.57, 0.5),
        (0, 44.65, 0.5),
        (0, 51.49, 0.5),
        (7.01, 62.36, 0.5),
        (34.65, 70.25, 0.5),
        (68.73, 77.07, 0.5),
        (109.22, 78.48, 0.5),
    ]
    assert draw.isComplete == True


def test_arrow_defaults() -> None:
    arrow = ArrowShape()
    assert arrow.style == Style(isFilled=False)
    assert arrow.childIndex == 1
    assert arrow.point == Position(0, 0)
    assert arrow.size == Size(0, 0)
    assert arrow.rotation == 0
    assert arrow.label is None
    assert arrow.labelPoint == Position(0.5, 0.5)

    assert arrow.bend == 0
    assert arrow.handles.start == Position(0, 0)
    assert arrow.handles.end == Position(1, 1)
    assert arrow.handles.bend == Position(0.5, 0.5)
    assert arrow.decorations.end == Decoration.ARROW
    assert arrow.decorations.start is None


def test_arrow_from_data() -> None:
    data: ShapeData = {
        "size": [52.20956955719355, 119.20196667928852],
        "label": "",
        "rotation": 0,
        "bend": -0.99,
        "id": "249aaa00-c3b4-4a72-15a4-10ff3ca3bac8",
        "labelPoint": [0.5, 0.5],
        "decorations": {"end": "arrow"},
        "parentId": "1",
        "childIndex": 139.5,
        "name": "Arrow",
        "point": [983.77, 694.51],
        "style": {
            "isFilled": False,
            "size": "small",
            "scale": 1,
            "color": "black",
            "dash": "draw",
        },
        "handles": {
            "start": {
                "id": "start",
                "index": 0,
                "point": [-5.82, 120.31],
                "canBind": True,
            },
            "end": {"id": "end", "index": 1, "point": [-9.41, -0.55], "canBind": True},
            "bend": {"id": "bend", "index": 2, "point": [52.21, 58.1]},
        },
        "userId": "w_m7bhjsqt8jtb",
        "type": "arrow",
    }
    arrow = ArrowShape.from_data(data)
    assert arrow.style == Style(
        isFilled=False,
        size=SizeStyle.SMALL,
        scale=1,
        color=ColorStyle.BLACK,
        dash=DashStyle.DRAW,
    )
    assert arrow.childIndex == 139.5
    assert arrow.point == Position(983.77, 694.51)
    assert arrow.size == Size(52.20956955719355, 119.20196667928852)
    assert arrow.rotation == 0
    assert arrow.label is None
    assert arrow.labelPoint == Position(0.5, 0.5)

    assert arrow.bend == -0.99
    assert arrow.handles.start == Position(-5.82, 120.31)
    assert arrow.handles.end == Position(-9.41, -0.55)
    assert arrow.handles.bend == Position(52.21, 58.1)
    assert arrow.decorations.end == Decoration.ARROW
    assert arrow.decorations.start is None
