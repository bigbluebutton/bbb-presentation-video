# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List, Optional, Protocol, Tuple, Type, TypeVar, Union

import attr
import cairo

from bbb_presentation_video.events import Size
from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.utils import Bounds, DrawPoints, Style

BaseShapeSelf = TypeVar("BaseShapeSelf", bound="BaseShape")


@attr.s(order=False, slots=True, auto_attribs=True)
class BaseShape:
    """The base class for all tldraw shapes."""

    style: Style = attr.Factory(Style)
    """Style related properties, such as color, line size, font."""
    childIndex: float = 1.0
    """Unsure: possibly z-position of this shape within a group?"""
    point: Position = Position(0.0, 0.0)
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


@attr.s(order=False, slots=True, auto_attribs=True)
class DrawShape(BaseShape):
    points: DrawPoints = []
    isComplete: bool = False

    # RotatableShapeProto
    size: Size = Size(0.0, 0.0)
    rotation: float = 0.0

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


@attr.s(order=False, slots=True, auto_attribs=True)
class RectangleShape(BaseShape):
    # LabelledShapeProto
    label: Optional[str] = None
    labelPoint: Position = Position(0.5, 0.5)

    # RotatableShapeProto
    size: Size = Size(1.0, 1.0)
    rotation: float = 0.0

    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        LabelledShapeProto.update_from_data(self, data)
        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@attr.s(order=False, slots=True, auto_attribs=True)
class EllipseShape(BaseShape):
    radius: Tuple[float, float] = (1.0, 1.0)

    # LabelledShapeProto
    label: Optional[str] = None
    labelPoint: Position = Position(0.5, 0.5)

    # RotatableShapeProto
    size: Size = Size(1.0, 1.0)
    rotation: float = 0.0

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


@attr.s(order=False, slots=True, auto_attribs=True)
class TriangleShape(BaseShape):
    # LabelledShapeProto
    label: Optional[str] = None
    labelPoint: Position = Position(0.5, 0.5)

    # RotatableShapeProto
    size: Size = Size(1.0, 1.0)
    rotation: float = 0.0

    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        LabelledShapeProto.update_from_data(self, data)
        RotatableShapeProto.update_from_data(self, data)

        self.cached_path = None
        self.cached_outline_path = None


@attr.s(order=False, slots=True, auto_attribs=True)
class TextShape(BaseShape):
    text: str = ""

    # RotatableShapeProto
    size: Size = Size(0.0, 0.0)
    rotation: float = 0.0

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]

        RotatableShapeProto.update_from_data(self, data)


@attr.s(order=False, slots=True, auto_attribs=True)
class GroupShape(BaseShape):
    # children: List[str]
    # size: Size
    # rotation: float

    pass


@attr.s(order=False, slots=True, auto_attribs=True)
class StickyShape(BaseShape):
    text: str = ""

    # RotatableShapeProto
    size: Size = Size(200.0, 200.0)
    rotation: float = 0.0

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "text" in data:
            self.text = data["text"]

        RotatableShapeProto.update_from_data(self, data)


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowHandle:
    point: Position = Position(0.0, 0.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowHandles:
    start: ArrowHandle = ArrowHandle()
    end: ArrowHandle = ArrowHandle()
    bend: ArrowHandle = ArrowHandle()


@attr.s(order=False, slots=True, auto_attribs=True)
class ArrowShape(BaseShape):
    bend: float = 0.0
    handles: ArrowHandles = ArrowHandles()

    # LabelledShapeProto
    label: Optional[str] = None
    labelPoint: Position = Position(0.5, 0.5)

    # RotatableShapeProto
    size: Size = Size(0.0, 0.0)
    rotation: float = 0.0

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "bend" in data:
            self.bend = data["bend"]

        LabelledShapeProto.update_from_data(self, data)
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


CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def apply_shape_rotation(
    ctx: "cairo.Context[CairoSomeSurface]", shape: RotatableShapeProto
) -> None:
    x = shape.size.width / 2
    y = shape.size.height / 2
    ctx.translate(x, y)
    ctx.rotate(shape.rotation)
    ctx.translate(-x, -y)
