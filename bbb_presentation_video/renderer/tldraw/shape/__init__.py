# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Dict, Optional, Protocol, Tuple, Type, TypeVar, Union

import attr
import cairo

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import HandleData, ShapeData
from bbb_presentation_video.renderer.tldraw.utils import Decoration, DrawPoints, Style

BaseShapeSelf = TypeVar("BaseShapeSelf", bound="BaseShapeProto")


@attr.s(order=False, slots=True, auto_attribs=True)
class BaseShapeProto(Protocol):
    """The base class for all tldraw shapes."""

    style: Style = attr.Factory(Style)
    """Style related properties, such as color, line size, font."""
    childIndex: float = 1
    """Unsure: possibly z-position of this shape within a group?"""
    point: Position = Position(0, 0)
    """Position of the origin of the shape."""

    @classmethod
    def from_data(cls: Type[BaseShapeSelf], data: ShapeData) -> BaseShapeSelf:
        shape = cls()
        shape.update_from_data(data)
        return shape

    def update_from_data(self, data: ShapeData) -> None:
        if "style" in data:
            self.style.update_from_data(data["style"])
        if "childIndex" in data:
            self.childIndex = data["childIndex"]
        if "point" in data:
            point = data["point"]
            self.point = Position(point[0], point[1])


@attr.s(order=False, slots=True, auto_attribs=True)
class SizedShapeProto(BaseShapeProto, Protocol):
    """The size fields that is common to many shapes."""

    size: Size = Size(0, 0)
    """Precalculated bounding box of the shape."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "size" in data:
            self.size = Size(data["size"])


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
        if "isComplete" in data:
            self.isComplete = data["isComplete"]


@attr.s(order=False, slots=True, auto_attribs=True)
class RectangleShape(LabelledShapeProto):
    # SizedShapeProto
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
class TriangleShape(LabelledShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShape(RotatableShapeProto):
    text: str = ""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]


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


Shape = Union[
    DrawShape,
    RectangleShape,
    EllipseShape,
    TriangleShape,
    ArrowShape,
    TextShape,
    GroupShape,
    StickyShape,
]


def parse_shape_from_data(data: ShapeData) -> Shape:
    type = data["type"]
    if type == "draw":
        return DrawShape.from_data(data)
    elif type == "rectangle":
        return RectangleShape.from_data(data)
    elif type == "ellipse":
        return EllipseShape.from_data(data)
    elif type == "triangle":
        return TriangleShape.from_data(data)
    elif type == "arrow":
        return ArrowShape.from_data(data)
    elif type == "text":
        return TextShape.from_data(data)
    elif type == "group":
        return GroupShape.from_data(data)
    elif type == "sticky":
        return StickyShape.from_data(data)
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
