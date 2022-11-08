# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List, Optional, Protocol, Tuple, Type, TypeVar, Union

import cairo
from attrs import define

from bbb_presentation_video.events import Size
from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.utils import Bounds, Style

BaseShapeSelf = TypeVar("BaseShapeSelf", bound="BaseShape")


@define
class BaseShape:
    """The base class for all tldraw shapes."""

    data: ShapeData
    """A copy of the original JSON shape data from tldraw, for handling updates."""
    style: Style
    """Style related properties, such as color, line size, font."""
    childIndex: float
    """Unsure: possibly z-position of this shape within a group?"""
    point: Position
    """Position of the origin of the shape."""

    def update_from_data(self, data: ShapeData) -> None:
        self.data = data

        if "style" in data:
            self.style = Style.from_data(data["style"])
        if "parentId" in data:
            self.parentId = data["parentId"]
        if "childIndex" in data:
            self.childIndex = data["childIndex"]
        if "point" in data:
            self.point = Position(*data["point"])

    @classmethod
    def from_data(cls: Type[BaseShapeSelf], data: ShapeData) -> BaseShapeSelf:
        shape = cls.__new__(cls)
        shape.update_from_data(data)
        return shape


class RotatableShapeProto(Protocol):
    """The size and rotation fields that are common to many shapes."""

    size: Size
    rotation: float

    def update_from_data(self, data: ShapeData) -> None:
        """Update the common size and rotation fields."""
        if "size" in data:
            self.size = Size(*data["size"])
        if "rotation" in data:
            self.rotation = data["rotation"]


class LabelledShapeProto(Protocol):
    style: Style
    size: Size
    label: Optional[str]
    labelPoint: Position

    def update_from_data(self, data: ShapeData) -> None:
        if "label" in data:
            self.label = data["label"] if data["label"] != "" else None
        if "labelPoint" in data:
            self.labelPoint = Position(*data["labelPoint"])


def shape_sort_key(shape: BaseShape) -> float:
    return shape.childIndex


DrawPoints = List[Union[Tuple[float, float], Tuple[float, float, float]]]


@define
class DrawShape(BaseShape):
    points: DrawPoints
    isComplete: bool
    size: Size
    rotation: float
    cached_bounds: Optional[Bounds] = None
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        RotatableShapeProto.update_from_data(self, data)

        if "points" in data:
            self.points = []
            for point in data["points"]:
                if len(point) == 3:
                    self.points.append((point[0], point[1], point[2]))
                else:
                    self.points.append((point[0], point[1]))
        if "isComplete" in data:
            self.isComplete = data["isComplete"]

        self.cached_bounds = None
        self.cached_path = None
        self.cached_outline_path = None


@define
class RectangleShape(BaseShape):
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        LabelledShapeProto.update_from_data(self, data)
        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@define
class EllipseShape(BaseShape):
    radius: Tuple[float, float]
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "radius" in data:
            radius = data["radius"]
            self.radius = (radius[0], radius[1])

        LabelledShapeProto.update_from_data(self, data)
        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@define
class TriangleShape(BaseShape):
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        LabelledShapeProto.update_from_data(self, data)
        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@define
class TextShape(BaseShape):
    text: str
    size: Size
    rotation: float

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]

        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@define
class GroupShape(BaseShape):
    # children: List[str]
    # size: Size
    # rotation: float
    pass


@define
class StickyShape(BaseShape):
    text: str
    size: Size
    rotation: float

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]

        RotatableShapeProto.update_from_data(self, data)


@define
class ArrowHandle:
    point: Position


@define
class ArrowHandles:
    start: ArrowHandle
    end: ArrowHandle
    bend: ArrowHandle


@define
class ArrowShape(BaseShape):
    label: Optional[str]
    labelPoint: Position
    bend: float
    handles: ArrowHandles
    size: Size
    rotation: float

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        RotatableShapeProto.update_from_data(self, data)


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


def apply_shape_rotation(ctx: cairo.Context, shape: RotatableShapeProto) -> None:
    x = shape.size.width / 2
    y = shape.size.height / 2
    ctx.translate(x, y)
    ctx.rotate(shape.rotation)
    ctx.translate(-x, -y)
