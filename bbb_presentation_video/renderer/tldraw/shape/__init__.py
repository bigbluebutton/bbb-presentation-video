# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Tuple, Type, TypeVar, Union

import attr
import cairo
from packaging.version import Version

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import HandleData, ShapeData
from bbb_presentation_video.renderer.tldraw.utils import (
    AlignStyle,
    Decoration,
    DrawPoints,
    GeoShape,
    SplineType,
    Style,
)

BaseShapeSelf = TypeVar("BaseShapeSelf", bound="BaseShapeProto")


@attr.s(order=False, slots=True, auto_attribs=True)
class BaseShapeProto(Protocol):
    """The base class for all tldraw shapes."""

    id: str = ""
    """ID of the shape."""
    style: Style = attr.Factory(Style)
    """Style related properties, such as color, line size, font."""
    childIndex: float = 1
    """Unsure: possibly z-position of this shape within a group?"""
    point: Position = Position(0, 0)
    """Position of the origin of the shape."""
    opacity: float = 1.0
    """Opacity of the shape."""
    parentId: str = ""
    """ID of the parent shape."""
    children: List[Shape] = []
    """List of children shapes."""

    @classmethod
    def from_data(cls: Type[BaseShapeSelf], data: ShapeData) -> BaseShapeSelf:
        shape = cls()
        shape.update_from_data(data)
        return shape

    def update_from_data(self, data: ShapeData) -> None:
        if "style" in data:
            self.style.update_from_data(data["style"])

        if "props" in data:
            self.style.update_from_data(data["props"])

        if "childIndex" in data:
            self.childIndex = data["childIndex"]

        if "point" in data:
            point = data["point"]
            self.point = Position(point[0], point[1])

        elif "x" in data and "y" in data:
            self.point = Position(data["x"], data["y"])

        if "opacity" in data:
            self.style.opacity = data["opacity"]

        if "parentId" in data:
            self.parentId = data["parentId"]


@attr.s(order=False, slots=True, auto_attribs=True)
class SizedShapeProto(BaseShapeProto, Protocol):
    """The size fields that is common to many shapes."""

    size: Size = Size(0, 0)
    """Precalculated bounding box of the shape."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "size" in data:
            self.size = Size(data["size"])

        if "props" in data:
            props = data["props"]

            if "w" in props and "h" in props:
                growY = 0.0

                if "growY" in props:
                    growY = props["growY"]

                self.size = Size(props["w"], props["h"] + growY)


@attr.s(order=False, slots=True, auto_attribs=True)
class RotatableShapeProto(SizedShapeProto, Protocol):
    rotation: float = 0
    """Rotation of the shape, in radians clockwise."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "rotation" in data:
            self.rotation = data["rotation"]


@attr.s(order=False, slots=True, auto_attribs=True)
class LabelledShapeProto(RotatableShapeProto, Protocol):
    """Properties common to shapes that can have labels."""

    label: Optional[str] = None
    """The text of the label."""
    labelPoint: Position = Position(0.5, 0.5)
    """The position of the label within the shape. Ranges from 0 to 1."""

    align: AlignStyle = AlignStyle.MIDDLE
    """Horizontal alignment of the label."""

    verticalAlign: AlignStyle = AlignStyle.MIDDLE
    """Vertical alignment of the label."""

    geo: GeoShape = GeoShape.NONE
    """Which geo type the shape is, if any."""

    def label_offset(self) -> Position:
        """Calculate the offset needed when drawing the label for most shapes."""
        return Position(
            (self.labelPoint.x - 0.5) * self.size.width,
            (self.labelPoint.y - 0.5) * self.size.height,
        )

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "label" in data:
            self.label = data["label"] if data["label"] != "" else None
        if "labelPoint" in data:
            self.labelPoint = Position(data["labelPoint"])
        if "children" in data:
            self.children = data["children"]
        if "props" in data:
            props = data["props"]

            if "text" in props:
                self.label = props["text"]
            if "align" in props:
                self.align = AlignStyle(props["align"])
            if "verticalAlign" in props:
                self.verticalAlign = AlignStyle(props["verticalAlign"])
            if "geo" in props:
                self.geo = GeoShape(props["geo"])
            if "w" in props and "h" in props and "name" in props:
                if not props["name"] == "":
                    self.label = props["name"]


def shape_sort_key(shape: BaseShapeProto) -> float:
    return shape.childIndex


@attr.s(order=False, slots=True, auto_attribs=True)
class DrawShape(RotatableShapeProto):
    points: DrawPoints = []
    """List of input points from the drawing tool."""
    isComplete: bool = False
    """Whether the last point in the line is present (pen lifted)."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "points" in data:
            self.points = []
            for point in data["points"]:
                if len(point) == 3:
                    self.points.append((point[0], point[1], point[2]))
                else:
                    self.points.append((point[0], point[1]))

        elif "props" in data and "segments" in data["props"]:
            self.points = []
            for segment in data["props"]["segments"]:
                if (
                    isinstance(segment, dict)
                    and "points" in segment
                    and isinstance(segment["points"], list)
                ):
                    for point in segment["points"]:
                        if isinstance(point, dict) and "x" in point and "y" in point:
                            if "z" in point:
                                self.points.append((point["x"], point["y"], point["z"]))
                            else:
                                self.points.append((point["x"], point["y"]))

        if "isComplete" in data:
            self.isComplete = data["isComplete"]
        elif "props" in data and "isComplete" in data["props"]:
            self.isComplete = data["props"]["isComplete"]


@attr.s(order=False, slots=True, auto_attribs=True)
class HighlighterShape(RotatableShapeProto):
    points: DrawPoints = []
    """List of input points from the drawing tool."""
    isComplete: bool = False
    """Whether the last point in the line is present (pen lifted)."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data and "segments" in data["props"]:
            self.points = []
            for segment in data["props"]["segments"]:
                if (
                    isinstance(segment, dict)
                    and "points" in segment
                    and isinstance(segment["points"], list)
                ):
                    for point in segment["points"]:
                        if isinstance(point, dict) and "x" in point and "y" in point:
                            if "z" in point:
                                self.points.append((point["x"], point["y"], point["z"]))
                            else:
                                self.points.append((point["x"], point["y"]))

        if "isComplete" in data:
            self.isComplete = data["isComplete"]
        elif "props" in data and "isComplete" in data["props"]:
            self.isComplete = data["props"]["isComplete"]


@attr.s(order=False, slots=True, auto_attribs=True)
class RectangleShape(LabelledShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class RectangleGeo(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class EllipseShape(LabelledShapeProto):
    radius: Tuple[float, float] = (1.0, 1.0)
    """x and y radius of the ellipse."""

    # SizedShapeProto
    size: Size = Size(1.0, 1.0)

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "radius" in data:
            radius = data["radius"]
            self.radius = (radius[0], radius[1])


@attr.s(order=False, slots=True, auto_attribs=True)
class EllipseGeo(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class FrameShape(LabelledShapeProto, SizedShapeProto):
    label: str = "Frame"
    children: List[Shape] = []
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class TriangleShape(LabelledShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class TriangleGeo(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Diamond(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Trapezoid(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShape(RotatableShapeProto):
    text: str = ""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShape_v2(RotatableShapeProto):
    text: str = ""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            if "text" in data["props"]:
                self.text = data["props"]["text"]


@attr.s(order=False, slots=True, auto_attribs=True)
class Rhombus(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Hexagon(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Cloud(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Star(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class Oval(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class XBox(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class CheckBox(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowGeo(LabelledShapeProto):
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class GroupShape(BaseShapeProto):
    pass


@attr.s(order=False, slots=True, auto_attribs=True)
class StickyShape(RotatableShapeProto):
    text: str = ""

    # SizedShapeProto
    size: Size = Size(200.0, 200.0)

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]


@attr.s(order=False, slots=True, auto_attribs=True)
class StickyShape_v2(RotatableShapeProto):
    text: str = ""
    align: AlignStyle = AlignStyle.MIDDLE
    verticalAlign: AlignStyle = AlignStyle.MIDDLE
    size: Size = Size(200.0, 200.0)

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            props = data["props"]
            if "text" in props:
                self.text = props["text"]
            if "align" in props:
                self.align = AlignStyle(props["align"])
            if "verticalAlign" in props:
                self.verticalAlign = AlignStyle(props["verticalAlign"])
            if "growY" in props:
                self.size = Size(self.size.width, self.size.height + props["growY"])
                if props["growY"] != 0:
                    self.verticalAlign = AlignStyle.START


@attr.s(order=False, slots=True, auto_attribs=True, init=False)
class ArrowHandles:
    start: Position
    bend: Position
    end: Position

    def __init__(
        self,
        start: Position = Position(0.0, 0.0),
        bend: Position = Position(0.5, 0.5),
        end: Position = Position(1.0, 1.0),
    ) -> None:
        self.start = start
        self.bend = bend
        self.end = end

    def update_from_data(self, data: Dict[str, HandleData]) -> None:
        try:
            self.start = Position(data["start"]["point"])
        except KeyError:
            pass
        try:
            self.bend = Position(data["bend"]["point"])
        except KeyError:
            pass
        try:
            self.end = Position(data["end"]["point"])
        except KeyError:
            pass


@attr.s(order=False, slots=True, auto_attribs=True, init=False)
class LineHandles:
    start: Position
    controlPoint: Position
    end: Position

    def __init__(
        self,
        start: Position = Position(0.0, 0.0),
        end: Position = Position(1.0, 1.0),
        controlPoint: Position = Position(0.5, 0.5),
    ) -> None:
        self.start = start
        self.controlPoint = controlPoint
        self.end = end

    def update_from_data(self, data: Dict[str, HandleData]) -> None:

        if "start" in data:
            if "point" in data["start"]:
                self.start = Position(data["start"]["point"])
            elif "x" in data["start"] and "y" in data["start"]:
                self.start = Position(data["start"]["x"], data["start"]["y"])

        if "end" in data:
            if "point" in data["end"]:
                self.end = Position(data["end"]["point"])
            elif "x" in data["end"] and "y" in data["end"]:
                self.end = Position(data["end"]["x"], data["end"]["y"])

        if "handle:a1V" in data:
            if "x" in data["handle:a1V"] and "y" in data["handle:a1V"]:
                self.controlPoint = Position(
                    data["handle:a1V"]["x"], data["handle:a1V"]["y"]
                )


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowDecorations:
    start: Optional[Decoration] = None
    end: Optional[Decoration] = Decoration.ARROW

    def update_from_data(self, data: Dict[str, Optional[str]]) -> None:
        self.start = Decoration(data["start"]) if "start" in data else None
        self.end = Decoration(data["end"]) if "end" in data else None


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowShape(LabelledShapeProto):
    bend: float = 0.0
    """Ratio of the bend to the distance between the start and end points.
    Negative if the bend point is to the left, otherwise positive."""
    handles: ArrowHandles = attr.Factory(ArrowHandles)
    """Locations of the line start, end, and bend points."""
    decorations: ArrowDecorations = attr.Factory(ArrowDecorations)
    """Whether the arrow head decorations are present on start/end of the line."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "bend" in data:
            self.bend = data["bend"]
        if "handles" in data:
            self.handles.update_from_data(data["handles"])
        if "decorations" in data:
            self.decorations.update_from_data(data["decorations"])


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowShape_v2(LabelledShapeProto):
    bend: float = 0.0
    handles: ArrowHandles = attr.Factory(ArrowHandles)
    """Locations of the line start, end, and bend points."""
    decorations: ArrowDecorations = attr.Factory(ArrowDecorations)
    """Whether the arrow head decorations are present on start/end of the line."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            props = data["props"]

            if "bend" in props:
                self.bend = props["bend"]
            if "start" in props:
                if "x" in props["start"] and "y" in props["start"]:
                    self.handles.start = Position(
                        props["start"]["x"], props["start"]["y"]
                    )
            if "end" in props:
                if "x" in props["end"] and "y" in props["end"]:
                    self.handles.end = Position(props["end"]["x"], props["end"]["y"])
            if "arrowheadStart" in props:
                self.decorations.start = Decoration(props["arrowheadStart"])
            if "arrowheadEnd" in props:
                self.decorations.end = Decoration(props["arrowheadEnd"])


@attr.s(order=False, slots=True, auto_attribs=True)
class LineShape(LabelledShapeProto):
    handles: LineHandles = attr.Factory(LineHandles)
    """Locations of the line start, end, and bend points."""
    spline: SplineType = SplineType.NONE
    """Whether a bent line is straight or curved."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "props" in data:
            if "handles" in data["props"]:
                self.handles.update_from_data(data["props"]["handles"])
            if "spline" in data["props"]:
                spline_prop = data["props"]["spline"]

                if spline_prop == "line":
                    self.spline = SplineType.LINE
                elif spline_prop == "cubic":
                    self.spline = SplineType.CUBIC
                else:
                    self.spline = SplineType.NONE


Shape = Union[
    ArrowShape,
    ArrowShape_v2,
    Diamond,
    DrawShape,
    EllipseGeo,
    EllipseShape,
    FrameShape,
    GroupShape,
    HighlighterShape,
    LineShape,
    RectangleGeo,
    RectangleShape,
    StickyShape,
    StickyShape_v2,
    TextShape,
    TextShape_v2,
    Trapezoid,
    TriangleGeo,
    TriangleShape,
    Rhombus,
    Hexagon,
    Cloud,
    Star,
    Oval,
    XBox,
    CheckBox,
    ArrowGeo,
]


def parse_shape_from_data(data: ShapeData, bbb_version: Version) -> Shape:
    type = data["type"]
    is_tldraw_v2 = bbb_version >= Version("3.0.0")

    if type == "draw":
        return DrawShape.from_data(data)
    elif type == "rectangle":
        return RectangleShape.from_data(data)
    elif type == "ellipse":
        return EllipseShape.from_data(data)
    elif type == "triangle":
        return TriangleShape.from_data(data)
    elif type == "arrow":
        if not is_tldraw_v2:
            return ArrowShape.from_data(data)
        else:
            return ArrowShape_v2.from_data(data)
    elif type == "text":
        if not is_tldraw_v2:
            return TextShape.from_data(data)
        else:
            return TextShape_v2.from_data(data)
    elif type == "group":
        return GroupShape.from_data(data)
    elif type == "sticky":
        return StickyShape.from_data(data)
    elif type == "note":
        return StickyShape_v2.from_data(data)
    elif type == "line":
        return LineShape.from_data(data)
    elif type == "highlight":
        return HighlighterShape.from_data(data)
    elif type == "frame":
        return FrameShape.from_data(data)
    elif type == "geo":
        if "geo" in data["props"]:
            geo_type = GeoShape(data["props"]["geo"])

            if geo_type is GeoShape.DIAMOND:
                return Diamond.from_data(data)
            if geo_type is GeoShape.ELLIPSE:
                return EllipseGeo.from_data(data)
            if geo_type is GeoShape.RECTANGLE:
                return RectangleGeo.from_data(data)
            if geo_type is GeoShape.TRIANGLE:
                return TriangleGeo.from_data(data)
            if geo_type is GeoShape.TRAPEZOID:
                return Trapezoid.from_data(data)
            if geo_type is GeoShape.RHOMBUS:
                return Rhombus.from_data(data)
            if geo_type is GeoShape.HEXAGON:
                return Hexagon.from_data(data)
            if geo_type is GeoShape.CLOUD:
                return Cloud.from_data(data)
            if geo_type is GeoShape.STAR:
                return Star.from_data(data)
            if geo_type is GeoShape.OVAL:
                return Oval.from_data(data)
            if geo_type is GeoShape.CHECKBOX:
                return CheckBox.from_data(data)
            if geo_type is GeoShape.XBOX:
                return XBox.from_data(data)
            if geo_type in [
                GeoShape.ARROW_DOWN,
                GeoShape.ARROW_LEFT,
                GeoShape.ARROW_RIGHT,
                GeoShape.ARROW_UP,
            ]:
                return ArrowGeo.from_data(data)
        raise Exception(f"Unknown geo shape: {type}")
    else:
        raise Exception(f"Unknown shape type: {type}")


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def apply_shape_rotation(
    ctx: cairo.Context[CairoSomeSurface], shape: RotatableShapeProto
) -> None:
    x = shape.size.width / 2
    y = shape.size.height / 2
    ctx.translate(x, y)
    ctx.rotate(shape.rotation)
    ctx.translate(-x, -y)
