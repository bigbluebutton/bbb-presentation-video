# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any, Iterable, List, Optional, Protocol, Tuple, Type, Union

import cairo
from attrs import define
from cattrs import Converter, structure_attrs_fromdict

from bbb_presentation_video.events import Size
from bbb_presentation_video.events.helpers import Position
from bbb_presentation_video.renderer.tldraw.utils import Bounds, Style

converter = Converter()


def position_structure_hook(o: Any, cl: Type[Position]) -> Position:
    if isinstance(o, Iterable):
        i = iter(o)
        x = next(i)
        y = next(i)
        return Position(x, y)
    else:
        return structure_attrs_fromdict(o, cl)


converter.register_structure_hook(Position, position_structure_hook)


def size_structure_hook(o: Any, cl: Type[Size]) -> Size:
    if isinstance(o, Iterable):
        i = iter(o)
        width = next(i)
        height = next(i)
        return Size(width, height)
    else:
        return structure_attrs_fromdict(o, cl)


converter.register_structure_hook(Size, size_structure_hook)


@define
class BaseShape:
    style: Style
    parentId: str
    childIndex: float
    point: Position


class RotatableShapeProto(Protocol):
    size: Size
    rotation: float


class LabelledShapeProto(Protocol):
    style: Style
    size: Size
    label: Optional[str]
    labelPoint: Position


def shape_sort_key(shape: BaseShape) -> float:
    return shape.childIndex


@define
class DrawShape(BaseShape):
    points: List[Tuple[float, float]]
    isComplete: bool
    size: Size
    rotation: float
    cached_bounds: Optional[Bounds] = None
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None


@define
class RectangleShape(BaseShape):
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None


@define
class EllipseShape(BaseShape):
    radius: Tuple[float, float]
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None


@define
class TriangleShape(BaseShape):
    label: Optional[str]
    labelPoint: Position
    size: Size
    rotation: float
    cached_path: Optional[cairo.Path] = None
    cached_outline_path: Optional[cairo.Path] = None


@define
class TextShape(BaseShape):
    text: str
    size: Size
    rotation: float


@define
class GroupShape(BaseShape):
    children: List[str]
    size: Size
    rotation: float


@define
class StickyShape(BaseShape):
    text: str
    size: Size
    rotation: float


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


def shape_structure_hook(o: Any, cl: Shape) -> Shape:
    type = o["type"]
    if type == "draw":
        return converter.structure(o, DrawShape)
    elif type == "rectangle":
        return converter.structure(o, RectangleShape)
    elif type == "ellipse":
        return converter.structure(o, EllipseShape)
    elif type == "triangle":
        return converter.structure(o, TriangleShape)
    elif type == "arrow":
        return converter.structure(o, ArrowShape)
    elif type == "text":
        return converter.structure(o, TextShape)
    elif type == "group":
        return converter.structure(o, GroupShape)
    elif type == "sticky":
        return converter.structure(o, StickyShape)
    else:
        raise Exception(f"Unhandled Tldraw shape type: {type}")


converter.register_structure_hook(Shape, shape_structure_hook)  # type: ignore


def apply_shape_rotation(ctx: cairo.Context, shape: RotatableShapeProto) -> None:
    x = shape.size.width / 2
    y = shape.size.height / 2
    ctx.translate(x, y)
    ctx.rotate(shape.rotation)
    ctx.translate(-x, -y)
