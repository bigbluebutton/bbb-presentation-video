from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShape,
    DrawShape,
    HighlighterShape,
    LineShape,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    HIGHLIGHT_COLORS,
    ColorStyle,
    DashStyle,
    Decoration,
    SizeStyle,
    Style,
    SplineType,
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


def test_arrow_from_data_no_decorations() -> None:
    data: ShapeData = {
        "size": [13.42, 699.31],
        "label": "",
        "rotation": 0,
        "bend": -2.743172580401816e-7,
        "id": "06fd6107-381a-4133-32ac-9ffc2f67e030",
        "labelPoint": [0.5, 0.5],
        "decorations": {},
        "parentId": "1",
        "childIndex": 0,
        "name": "Arrow",
        "point": [199.43, 311.63],
        "style": {
            "isFilled": False,
            "size": "small",
            "scale": 1,
            "color": "black",
            "textAlign": "start",
            "font": "script",
            "dash": "draw",
        },
        "handles": {
            "start": {"id": "start", "index": 0, "point": [0, 699.31], "canBind": True},
            "end": {"id": "end", "index": 1, "point": [13.42, 0], "canBind": True},
            "bend": {"id": "bend", "index": 2, "point": [6.71, 349.66]},
        },
        "userId": "w_ojf9vuncwica",
        "type": "arrow",
    }
    arrow = ArrowShape.from_data(data)
    assert arrow.decorations.start is None
    assert arrow.decorations.end is None


def test_line_from_data() -> None:
    data: ShapeData = {
        "x": 1250,
        "isLocked": False,
        "y": 207,
        "rotation": 0,
        "typeName": "shape",
        "isModerator": True,
        "opacity": 1,
        "parentId": "page:1",
        "index": "a3",
        "id": "shape:O2QkpQBjAPe2V8hH6Co4X",
        "meta": {"updatedBy": "w_b3rm8exhwsjf"},
        "type": "line",
        "props": {
            "size": "m",
            "handles": {
                "start": {
                    "x": 0,
                    "canSnap": True,
                    "y": 0,
                    "canBind": False,
                    "id": "start",
                    "type": "vertex",
                    "index": "a1",
                },
                "end": {
                    "x": -229,
                    "canSnap": True,
                    "y": 377,
                    "canBind": False,
                    "id": "end",
                    "type": "vertex",
                    "index": "a2",
                },
                "handle:a1V": {
                    "x": -71,
                    "y": 216,
                    "canBind": False,
                    "id": "handle:a1V",
                    "type": "vertex",
                    "index": "a1V",
                },
            },
            "dash": "draw",
            "color": "red",
            "spline": "cubic",
        },
    }
    line = LineShape.from_data(data)
    assert line.style == Style(
        isFilled=False,
        size=SizeStyle.M,
        color=ColorStyle.RED,
        dash=DashStyle.DRAW,
    )

    assert line.spline == SplineType.CUBIC
    assert line.point == Position(1250, 207)
    assert line.rotation == 0
    assert line.label is None
    assert line.labelPoint == Position(0.5, 0.5)

    assert line.handles.start == Position(0, 0)
    assert line.handles.controlPoint == Position(-71, 216)
    assert line.handles.end == Position(-229, 377)


def test_highlight_from_data() -> None:
    data: ShapeData = {
        "x": 354,
        "isLocked": False,
        "y": 140,
        "rotation": 0,
        "typeName": "shape",
        "isModerator": True,
        "opacity": 1,
        "parentId": "page:1",
        "index": "a1",
        "id": "shape:S_7PT3QSaUT6dzHcRV8Eb",
        "meta": {"createdBy": "w_vxjirycsy2br"},
        "type": "highlight",
        "props": {
            "size": "xl",
            "color": "red",
            "isPen": False,
            "segments": [{"type": "free", "points": [{"x": 0, "y": 0, "z": 0.5}]}],
            "isComplete": False,
        },
    }

    highlight = HighlighterShape.from_data(data)
    assert highlight.style == Style(size=SizeStyle.XL, color=ColorStyle.RED)

    assert highlight.point == Position(354, 140)
    assert highlight.rotation == 0
