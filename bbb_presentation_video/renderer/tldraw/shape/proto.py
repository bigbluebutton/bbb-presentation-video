# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import List, Optional, Protocol, Type, TypeVar

import attr
import cairo

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import ShapeData
from bbb_presentation_video.renderer.tldraw.utils import AlignStyle, Style

BaseShapeSelf = TypeVar("BaseShapeSelf", bound="BaseShapeProto")
CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


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
    children: List[BaseShapeProto] = []
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

        if "children" in data:
            self.children = data["children"]

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

            w = 0.0
            h = 0.0
            growY = 0.0
            if "w" in props:
                w = props["w"]
            if "h" in props:
                h = props["h"]
            if "growY" in props:
                growY = props["growY"]

            self.size = Size(w, h + growY)


@attr.s(order=False, slots=True, auto_attribs=True)
class RotatableShapeProto(SizedShapeProto, Protocol):
    rotation: float = 0
    """Rotation of the shape, in radians clockwise."""

    def update_from_data(self, data: ShapeData) -> None:
        super().update_from_data(data)

        if "rotation" in data:
            self.rotation = data["rotation"]

    def apply_shape_rotation(self, ctx: cairo.Context[CairoSomeSurface]) -> None:
        x = self.size.width / 2
        y = self.size.height / 2
        ctx.translate(x, y)
        ctx.rotate(self.rotation)
        ctx.translate(-x, -y)


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
        if "props" in data:
            props = data["props"]

            if "text" in props:
                self.label = props["text"]
            if "align" in props:
                self.align = AlignStyle(props["align"])
            if "verticalAlign" in props:
                self.verticalAlign = AlignStyle(props["verticalAlign"])
            if "w" in props and "h" in props and "name" in props:
                if not props["name"] == "":
                    self.label = props["name"]
