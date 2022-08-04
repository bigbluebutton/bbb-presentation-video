from typing import TypedDict, Dict, Any
from lxml import etree

import json

from bbb_presentation_video.events.helpers import xml_subelement, Position


class AddShapeEvent(TypedDict):
    name: str
    id: str
    presentation: str
    slide: int
    user_id: str
    data: Dict[Any, Any]


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
