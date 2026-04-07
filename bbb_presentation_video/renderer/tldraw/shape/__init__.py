# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import attr
from packaging.version import Version

from bbb_presentation_video.events.helpers import Position, Size
from bbb_presentation_video.events.tldraw import HandleData, ShapeData
from bbb_presentation_video.renderer.tldraw.shape.proto import (
    BaseShapeProto,
    LabelledShapeProto,
    RotatableShapeProto,
)
from bbb_presentation_video.renderer.tldraw.shape.sticky import StickyShape
from bbb_presentation_video.renderer.tldraw.shape.text import TextShape
from bbb_presentation_video.renderer.tldraw.utils import (
    Decoration,
    DrawPoints,
    SplineType,
)
from bbb_presentation_video.renderer.tldraw.v2.shape.frame import FrameShape
from bbb_presentation_video.renderer.tldraw.v2.shape.geo import (
    ArrowDownGeoShape,
    ArrowLeftGeoShape,
    ArrowRightGeoShape,
    ArrowUpGeoShape,
    CheckBoxGeoShape,
    DiamondGeoShape,
    GeoShape,
    GeoShapeProto,
    HexagonGeoShape,
    OctagonGeoShape,
    PentagonGeoShape,
    RectangleGeoShape,
    Rhombus2GeoShape,
    RhombusGeoShape,
    StarGeoShape,
    TrapezoidGeoShape,
    TriangleGeoShape,
    XBoxGeoShape,
)
from bbb_presentation_video.renderer.tldraw.v2.shape.sticky import StickyShapeV2
from bbb_presentation_video.renderer.tldraw.v2.shape.text import TextShapeV2


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
class EllipseGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class TriangleShape(LabelledShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class CloudGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class OvalGeoShape(GeoShapeProto):
    # SizedShapeProto
    size: Size = Size(1.0, 1.0)


@attr.s(order=False, slots=True, auto_attribs=True)
class GroupShape(BaseShapeProto):
    pass


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
class ArrowShapeV2(LabelledShapeProto):
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


@attr.s(order=False, slots=True, auto_attribs=True)
class PollShapeAnswer:
    key: str
    numVotes: int


@attr.s(order=False, slots=True, auto_attribs=True)
class PollShape(RotatableShapeProto):
    question: str = ""
    numResponders: int = 0
    numRespondents: int = 0
    questionType: str = ""
    questionText: str = ""
    answers: List[PollShapeAnswer] = attr.Factory(list)

    def update_from_data(self, data: ShapeData) -> None:
        # Poll shapes contain a prop "fill" which isn't a valid FillStyle
        if "props" in data and "fill" in data["props"]:
            del data["props"]["fill"]

        super().update_from_data(data)

        if "props" in data:
            props = data["props"]
            if "question" in props:
                self.question = props["question"]
            if "numResponders" in props:
                self.numResponders = props["numResponders"]
            if "numRespondents" in props:
                self.numRespondents = props["numRespondents"]
            if "questionType" in props:
                self.questionType = props["questionType"]
            if "questionText" in props:
                self.questionText = props["questionText"]
            if "answers" in props:
                self.answers = [
                    PollShapeAnswer(key=answer["key"], numVotes=answer["numVotes"])
                    for answer in props["answers"]
                ]


def parse_shape_from_data(
    data: ShapeData, bbb_version: Version
) -> Optional[BaseShapeProto]:
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
        if is_tldraw_v2:
            return ArrowShapeV2.from_data(data)
        else:
            return ArrowShape.from_data(data)
    elif type == "text":
        if is_tldraw_v2:
            return TextShapeV2.from_data(data)
        else:
            return TextShape.from_data(data)
    elif type == "group":
        return GroupShape.from_data(data)
    elif type == "sticky":
        return StickyShape.from_data(data)
    elif type == "note":
        return StickyShapeV2.from_data(data)
    elif type == "line":
        return LineShape.from_data(data)
    elif type == "highlight":
        return HighlighterShape.from_data(data)
    elif type == "frame":
        return FrameShape.from_data(data)
    elif type == "poll":
        return PollShape.from_data(data)
    elif type == "geo":
        if "geo" in data["props"]:
            try:
                geo_type = GeoShape(data["props"]["geo"])
            except KeyError:
                print("\tTldraw: Ignoring unknown geo shape type")
                return None

            if geo_type is GeoShape.DIAMOND:
                return DiamondGeoShape.from_data(data)
            if geo_type is GeoShape.PENTAGON:
                return PentagonGeoShape.from_data(data)
            if geo_type is GeoShape.ELLIPSE:
                return EllipseGeoShape.from_data(data)
            if geo_type is GeoShape.RECTANGLE:
                return RectangleGeoShape.from_data(data)
            if geo_type is GeoShape.TRIANGLE:
                return TriangleGeoShape.from_data(data)
            if geo_type is GeoShape.TRAPEZOID:
                return TrapezoidGeoShape.from_data(data)
            if geo_type is GeoShape.RHOMBUS:
                return RhombusGeoShape.from_data(data)
            if geo_type is GeoShape.RHOMBUS_2:
                return Rhombus2GeoShape.from_data(data)
            if geo_type is GeoShape.HEXAGON:
                return HexagonGeoShape.from_data(data)
            if geo_type is GeoShape.OCTAGON:
                return OctagonGeoShape.from_data(data)
            if geo_type is GeoShape.CLOUD:
                return CloudGeoShape.from_data(data)
            if geo_type is GeoShape.STAR:
                return StarGeoShape.from_data(data)
            if geo_type is GeoShape.OVAL:
                return OvalGeoShape.from_data(data)
            if geo_type is GeoShape.CHECKBOX:
                return CheckBoxGeoShape.from_data(data)
            if geo_type is GeoShape.XBOX:
                return XBoxGeoShape.from_data(data)
            if geo_type is GeoShape.ARROW_RIGHT:
                return ArrowRightGeoShape.from_data(data)
            if geo_type is GeoShape.ARROW_LEFT:
                return ArrowLeftGeoShape.from_data(data)
            if geo_type is GeoShape.ARROW_UP:
                return ArrowUpGeoShape.from_data(data)
            if geo_type is GeoShape.ARROW_DOWN:
                return ArrowDownGeoShape.from_data(data)

        print("\tTldraw: No shape for geo shape type {geo_type}, skipping")
        return None

    else:
        print(f"\tTldraw: Ignoring unknown shape of type '{type}'")
        return None
