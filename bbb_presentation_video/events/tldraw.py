# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from typing import Any, Collection, Dict, List, Optional, Sequence, TypedDict, Union

from lxml import etree

from bbb_presentation_video.events.helpers import Position, xml_subelement


class StyleData(TypedDict, total=False):
    dash: str
    font: str
    isFilled: bool
    scale: float
    textAlign: str
    opacity: float
    isComplete: bool
    fill: str
    color: str
    size: str
    isClosed: bool
    segments: List[Dict[str, Sequence[Collection[str]]]]


class HandleData(TypedDict, total=False):
    bindingId: str
    canBind: bool
    canSnap: bool
    id: str
    index: Union[str, int]
    point: List[float]
    type: str
    x: float
    y: float


class PropsData(StyleData, total=False):
    align: str
    arrowheadEnd: str
    arrowheadStart: str
    bend: float
    end: HandleData
    geo: str
    handles: Dict[str, HandleData]
    isPen: bool
    spline: str
    start: HandleData
    text: str
    verticalAlign: str
    w: float
    h: float
    growY: float
    name: str


class ShapeData(TypedDict, total=False):
    bend: float
    childIndex: float
    decorations: Dict[str, Optional[str]]
    handles: Dict[str, HandleData]
    id: str
    index: Union[int, str]
    isComplete: bool
    isLocked: bool
    isModerator: bool
    label: str
    labelPoint: List[float]
    meta: Dict[str, str]
    name: str
    opacity: float
    parentId: str
    point: List[float]
    points: List[List[float]]
    props: PropsData
    radius: List[float]
    rotation: float
    size: List[float]
    style: StyleData
    text: str
    type: str
    typeName: str
    userId: str
    x: float
    y: float
    children: List[Any]


class AddShapeEvent(TypedDict):
    name: str
    id: str
    presentation: str
    slide: int
    user_id: str
    data: ShapeData


def parse_add_shape(event: AddShapeEvent, element: etree._Element) -> None:
    name = event["name"]
    event["id"] = xml_subelement(element, name, "shapeId")
    event["presentation"] = xml_subelement(element, name, "presentation")
    event["slide"] = int(xml_subelement(element, name, "pageNumber"))
    event["user_id"] = xml_subelement(element, name, "userId")
    event["data"] = json.loads(xml_subelement(element, name, "shapeData"))
    event["name"] = "tldraw.add_shape"


class DeleteShapeEvent(TypedDict):
    name: str
    id: str
    presentation: str
    slide: int
    user_id: str


def parse_delete_shape(event: DeleteShapeEvent, element: etree._Element) -> None:
    name = event["name"]
    event["id"] = xml_subelement(element, name, "shapeId")
    event["presentation"] = xml_subelement(element, name, "presentation")
    event["slide"] = int(xml_subelement(element, name, "pageNumber"))
    event["user_id"] = xml_subelement(element, name, "userId")
    event["name"] = "tldraw.delete_shape"


class CameraChangedEvent(TypedDict):
    name: str
    pod: str
    presentation: str
    camera: Position
    zoom: float


def parse_camera_changed(event: CameraChangedEvent, element: etree._Element) -> None:
    name = event["name"]
    event["pod"] = xml_subelement(element, name, "podId")
    event["presentation"] = xml_subelement(element, name, "presentationName")
    # TODO: ``pageNumber`` (slide) and ``userId`` (user_id) should be added
    x = float(xml_subelement(element, name, "xCamera"))
    y = float(xml_subelement(element, name, "yCamera"))
    event["camera"] = Position(x, y)
    event["zoom"] = float(xml_subelement(element, name, "zoom"))
    event["name"] = "tldraw.camera"
