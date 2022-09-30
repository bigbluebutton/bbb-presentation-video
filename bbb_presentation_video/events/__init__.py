# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from collections import deque
from enum import Enum
from fractions import Fraction
from typing import Any, Deque, Dict, List, Optional, Tuple, TypedDict, cast

from attrs import define
from lxml import etree
from packaging.version import Version

from bbb_presentation_video.events import tldraw
from bbb_presentation_video.events.errors import *
from bbb_presentation_video.events.helpers import (
    Color,
    Position,
    xml_subelement,
    xml_subelement_opt,
    xml_subelement_shape_slide,
)

MAGIC_MYSTERY_NUMBER = 2.0
DEFAULT_PRESENTATION_POD = "DEFAULT_PRESENTATION_POD"


@define
class Size:
    width: float
    height: float

    def __str__(self) -> str:
        return f"{self.width:.3f}x{self.height:.3f}"

    def __mul__(self, other: float) -> "Size":
        return Size(self.width * other, self.height * other)


class ShapeStatus(Enum):
    DRAW_START = 1
    DRAW_UPDATE = 2
    DRAW_END = 3
    textCreated = 1
    textEdited = 2
    textPublished = 3


class PencilCommand(Enum):
    MOVE_TO = 1
    LINE_TO = 2
    Q_CURVE_TO = 3
    C_CURVE_TO = 4


class Event(TypedDict):
    name: str
    timestamp: Fraction


class PerPodEvent(Event):
    pod_id: str


class CursorEvent(Event):
    cursor: Optional[Position]


def parse_cursor(event: CursorEvent, element: etree._Element) -> None:
    name = event["name"]
    x = float(xml_subelement(element, name, "xOffset"))
    y = float(xml_subelement(element, name, "yOffset"))

    if 0 <= x <= 1 and 0 <= y <= 1:
        event["cursor"] = Position(x, y)
    else:
        event["cursor"] = None

    event["name"] = "cursor"


class WhiteboardCursorEvent(Event):
    presentation: Optional[str]
    slide: Optional[int]
    cursor: Optional[Position]
    user_id: str


def parse_whiteboard_cursor(
    event: WhiteboardCursorEvent, element: etree._Element, *, tldraw_whiteboard: bool
) -> None:
    event["presentation"] = xml_subelement_opt(element, "presentation")

    slide = xml_subelement_opt(element, "pageNumber")
    if slide is not None:
        event["slide"] = int(slide)

    x_offset = float(xml_subelement(element, event["name"], "xOffset"))
    y_offset = float(xml_subelement(element, event["name"], "yOffset"))
    cursor = None
    if tldraw_whiteboard:
        # Cursor in tldraw whiteboard coordinate system
        if x_offset >= 0 and y_offset >= 0:
            cursor = Position(x_offset, y_offset)
    else:
        # Cursor in BigBlueButton whiteboard coordinate system
        x_offset /= 100
        y_offset /= 100
        if 0 <= x_offset <= 1 and 0 <= y_offset <= 1:
            cursor = Position(x_offset, y_offset)
    event["cursor"] = cursor

    event["user_id"] = xml_subelement(element, event["name"], "userId")

    event["name"] = "cursor_v2"


class PanZoomEvent(PerPodEvent):
    pan: Position
    zoom: Size


def parse_pan_zoom(
    event: PanZoomEvent, element: etree._Element, *, tldraw_whiteboard: bool
) -> None:
    name = event["name"]

    x_offset = xml_subelement(element, name, "xOffset")
    y_offset = xml_subelement(element, name, "yOffset")
    # Workaround a bug where BBB can return 'NaN' in the values
    if x_offset == "NaN" or y_offset == "NaN":
        event["pan"] = Position(0.0, 0.0)
    else:
        if tldraw_whiteboard:
            event["pan"] = Position(float(x_offset), float(y_offset))
        else:
            event["pan"] = Position(
                float(x_offset) * MAGIC_MYSTERY_NUMBER / 100,
                float(y_offset) * MAGIC_MYSTERY_NUMBER / 100,
            )

    width_ratio = xml_subelement(element, name, "widthRatio")
    height_ratio = xml_subelement(element, name, "heightRatio")
    if width_ratio == "NaN" or height_ratio == "NaN":
        event["zoom"] = Size(1.0, 1.0)
    else:
        event["zoom"] = Size(float(width_ratio) / 100, float(height_ratio) / 100)
    # Workaround a bug where BBB can return a width or height ratio of 0,
    # which is nonsensical and causes divide-by-zero errors.
    # It can also return values less than zero, I dunno what's up with that.
    if event["zoom"].width <= 0 or event["zoom"].height <= 0:
        event["zoom"] = Size(1.0, 1.0)

    pod_id = xml_subelement_opt(element, "podId")
    event["pod_id"] = pod_id if pod_id is not None else DEFAULT_PRESENTATION_POD

    event["name"] = "pan_zoom"


class SlideEvent(PerPodEvent):
    slide: int


def parse_slide(event: SlideEvent, element: etree._Element) -> None:
    event["slide"] = int(xml_subelement(element, event["name"], "slide"))

    pod_id = xml_subelement_opt(element, "podId")
    event["pod_id"] = pod_id if pod_id is not None else DEFAULT_PRESENTATION_POD

    event["name"] = "slide"


class PresentationEvent(PerPodEvent):
    presentation: str


def parse_presentation(event: PresentationEvent, element: etree._Element) -> None:
    event["presentation"] = xml_subelement(element, event["name"], "presentationName")

    pod_id = xml_subelement_opt(element, "podId")
    event["pod_id"] = pod_id if pod_id is not None else DEFAULT_PRESENTATION_POD

    event["name"] = "presentation"


class ShapeEvent(Event):
    shape_type: str
    shape_id: Optional[str]
    shape_status: Optional[ShapeStatus]
    presentation: Optional[str]
    slide: Optional[int]
    user_id: Optional[str]
    points: List[Position]
    # Drawn shapes
    color: Color
    thickness: Optional[float]
    thickness_ratio: Optional[float]
    rounded: bool
    square: bool
    circle: bool
    commands: Optional[List[PencilCommand]]
    # Poll
    num_responders: int
    num_respondents: int
    result: Any
    # Text
    width: float
    height: float
    font_color: Color
    font_size: float
    calced_font_size: float
    text: str


def parse_shape(
    event: ShapeEvent,
    element: etree._Element,
    *,
    shape_thickness_percent: bool,
    shape_slide_off_by_one: bool,
    shape_rounded: bool,
) -> None:
    name = event["name"]

    # Common attributes for all shapes
    event["shape_id"] = xml_subelement_opt(element, "id")
    event["presentation"] = xml_subelement_opt(element, "presentation")
    event["shape_type"] = shape_type = xml_subelement(element, name, "type")
    event["slide"] = xml_subelement_shape_slide(element, shape_slide_off_by_one)

    status = xml_subelement_opt(element, "status")
    if status is not None:
        event["shape_status"] = ShapeStatus[status]

    event["user_id"] = xml_subelement_opt(element, "userId")

    data_points = xml_subelement_opt(element, "dataPoints")

    # We have to ignore draw events with an empty dataPoints. An example of
    # where this happens is in the DRAW_END event for the pencil tool when
    # server-side smoothing failed - the final event has no points, and we're
    # expected to use the existing shape as-is
    if data_points is None:
        raise ShapeNoDataPointsError(
            event["name"], shape_type, str(event["shape_status"])
        )

    # The 'dataPoints' element contains a list of alternating X and Y
    # coordinates. Collapse them into a collection of Positions
    points = []
    points_iter = iter(data_points.split(","))
    while True:
        try:
            points.append(
                Position(float(next(points_iter)) / 100, float(next(points_iter)) / 100)
            )
        except StopIteration:
            break
    event["points"] = points

    if shape_type in ["pencil", "rectangle", "ellipse", "triangle", "line"]:
        # These shapes share a bunch of attributes
        event["color"] = Color.from_int(int(xml_subelement(element, name, "color")))
        thickness = float(xml_subelement(element, name, "thickness"))
        if shape_thickness_percent:
            event["thickness_ratio"] = thickness / 100
        else:
            event["thickness"] = thickness

    # Pencil is always rounded; other shapes use flag
    event["rounded"] = shape_rounded or shape_type == "pencil"

    # Some extra attributes for special shapes
    if shape_type == "rectangle":
        square = xml_subelement_opt(element, "square")
        if square is not None:
            event["square"] = square == "true"
        else:
            event["square"] = False
    elif shape_type == "ellipse":
        circle = xml_subelement_opt(element, "circle")
        if circle is not None:
            event["circle"] = circle == "true"
        else:
            event["circle"] = False
    elif shape_type == "pencil":
        commands = xml_subelement_opt(element, "commands")
        if commands is not None:
            event["commands"] = [PencilCommand(int(x)) for x in commands.split(",")]

    elif shape_type == "poll_result":
        event["num_responders"] = int(xml_subelement(element, name, "num_responders"))
        event["num_respondents"] = int(xml_subelement(element, name, "num_respondents"))
        event["result"] = json.loads(xml_subelement(element, name, "result"))

    elif shape_type == "text":
        # Note that we don't need the X and Y; they're duplicated from
        # the dataPoints list.
        event["width"] = float(xml_subelement(element, name, "textBoxWidth")) / 100
        event["height"] = float(xml_subelement(element, name, "textBoxHeight")) / 100
        event["font_color"] = Color.from_int(
            int(xml_subelement(element, name, "fontColor"))
        )
        event["font_size"] = float(xml_subelement(element, name, "fontSize"))
        event["calced_font_size"] = (
            float(xml_subelement(element, name, "calcedFontSize")) / 100
        )
        event["text"] = xml_subelement_opt(element, "text") or ""
    else:
        raise UnknownShapeError(event["name"], shape_type)

    event["name"] = "shape"


class UndoEvent(Event):
    presentation: Optional[str]
    slide: Optional[int]
    user_id: Optional[str]
    shape_id: Optional[str]


def parse_undo(
    event: UndoEvent, element: etree._Element, *, shape_slide_off_by_one: bool
) -> None:
    event["presentation"] = xml_subelement_opt(element, "presentation")
    event["slide"] = xml_subelement_shape_slide(element, shape_slide_off_by_one)
    event["user_id"] = xml_subelement_opt(element, "userId")
    event["shape_id"] = xml_subelement_opt(element, "shapeId")
    event["name"] = "undo"


class ClearEvent(Event):
    presentation: Optional[str]
    slide: Optional[int]
    user_id: Optional[str]
    full_clear: Optional[bool]


def parse_clear(
    event: ClearEvent, element: etree._Element, *, shape_slide_off_by_one: bool
) -> None:
    event["presentation"] = xml_subelement_opt(element, "presentation")
    event["slide"] = xml_subelement_shape_slide(element, shape_slide_off_by_one)
    event["user_id"] = xml_subelement_opt(element, "userId")
    full_clear = xml_subelement_opt(element, "fullClear")
    if full_clear is not None:
        event["full_clear"] = full_clear == "true"
    event["name"] = "clear"


class RecordEvent(Event):
    status: bool


def parse_record(event: RecordEvent, element: etree._Element) -> None:
    event["status"] = xml_subelement(element, event["name"], "status") == "true"
    event["name"] = "record"


class PresenterEvent(PerPodEvent):
    user_id: str


def parse_presenter(event: PresenterEvent, element: etree._Element) -> None:
    event["user_id"] = xml_subelement(element, event["name"], "userid")
    event["pod_id"] = DEFAULT_PRESENTATION_POD
    event["name"] = "presenter"


def parse_pod_presenter(event: PresenterEvent, element: etree._Element) -> None:
    name = event["name"]
    event["user_id"] = xml_subelement(element, name, "nextPresenterId")
    event["pod_id"] = xml_subelement(element, name, "podId")
    event["name"] = "presenter"


class JoinEvent(Event):
    user_id: str
    user_name: str


def parse_join(event: JoinEvent, element: etree._Element) -> None:
    name = event["name"]
    event["user_id"] = xml_subelement(element, name, "userId")
    event["user_name"] = xml_subelement(element, name, "name")
    event["name"] = "join"


class LeftEvent(Event):
    user_id: str


def parse_left(event: LeftEvent, element: etree._Element) -> None:
    event["user_id"] = xml_subelement(element, event["name"], "userId")
    event["name"] = "left"


def parse_events(
    directory: str = ".",
) -> Tuple[Deque[Event], Optional[Fraction], bool, bool]:
    start_time = None
    last_timestamp = None
    have_record_events = False
    events: Deque[Event] = deque()

    root = etree.parse(f"{directory}/events.xml")
    root_e = root.getroot()
    print(f"Events: bbb_version: {root_e.get('bbb_version')}")

    use_pod_presenter = False
    shape_thickness_percent = False
    shape_slide_off_by_one = True
    shape_rounded = True
    try:
        bbb_version = Version(str(root_e.attrib["bbb_version"]))
        use_pod_presenter = bbb_version >= Version("2.1")
        shape_thickness_percent = bbb_version >= Version("2.0")
        shape_slide_off_by_one = not (bbb_version >= Version("0.9.0"))
        shape_rounded = not (bbb_version >= Version("2.0"))
        tldraw_whiteboard = bbb_version >= Version("2.6")
    except AttributeError:
        pass

    print(f"Events: shape_thickness_percent: {shape_thickness_percent}")
    print(f"Events: shape_slide_off_by_one: {shape_slide_off_by_one}")
    print(f"Events: tldraw_whiteboard: {tldraw_whiteboard}")

    metadata = root.find("metadata")
    if metadata is None:
        raise EventParsingError("N/A", "Missing metadata element.")
    hide_logo = metadata.get("bn-rec-hide-logo", "false") == "true"

    for element in root.iter("event"):
        try:

            # Convert timestamps to be in seconds from recording start
            ts_i = int(element.attrib["timestamp"])
            if not start_time:
                start_time = ts_i
            timestamp = Fraction(ts_i - start_time, 1000)

            # Save the timestamp of last event as recording length
            last_timestamp = timestamp

            module = element.attrib["module"]

            # Only need events from these modules
            if not module in [
                "PRESENTATION",
                "WHITEBOARD",
                "PARTICIPANT",
            ]:
                continue

            name = str(element.attrib["eventname"])
            event: Event = {
                "name": name,
                "timestamp": timestamp,
            }

            if module == "PARTICIPANT":
                if name == "AssignPresenterEvent":
                    if use_pod_presenter:
                        # Ignore the duplicate legacy presenter event if per-pod presenter is available.
                        continue
                    else:
                        parse_presenter(cast(PresenterEvent, event), element)
                elif name == "ParticipantJoinEvent":
                    parse_join(cast(JoinEvent, event), element)
                elif name == "ParticipantLeftEvent":
                    parse_left(cast(LeftEvent, event), element)
                elif name == "RecordStatusEvent":
                    parse_record(cast(RecordEvent, event), element)
                    have_record_events = True
                else:
                    # Only interested in a few specific participant event, new events are unlikely to
                    # mean recordings will be incorrect.
                    continue

            elif module == "PRESENTATION":
                if name == "CursorMoveEvent":
                    parse_cursor(cast(CursorEvent, event), element)
                elif name == "GotoSlideEvent":
                    parse_slide(cast(SlideEvent, event), element)
                elif name == "ResizeAndMoveSlideEvent":
                    parse_pan_zoom(
                        cast(PanZoomEvent, event),
                        element,
                        tldraw_whiteboard=tldraw_whiteboard,
                    )
                elif name == "SetPresenterInPodEvent":
                    parse_pod_presenter(cast(PresenterEvent, event), element)
                elif name == "SharePresentationEvent":
                    parse_presentation(cast(PresentationEvent, event), element)
                elif name == "TldrawCameraChangedEvent":
                    tldraw.parse_camera_changed(
                        cast(tldraw.CameraChangedEvent, event), element
                    )
                # Unused events
                elif (
                    name == "CreatePresentationPodEvent"
                    or name == "ConversionCompletedEvent"
                    or name == "GenerateSlideEvent"
                    or name == "SetPresentationDownloadable"
                ):
                    continue
                else:
                    # Unknown presentation events probably mean recording rendering will be incorrect.
                    raise UnknownEventError(event["name"])

            elif module == "WHITEBOARD":
                if name == "AddShapeEvent" or name == "ModifyTextEvent":
                    parse_shape(
                        cast(ShapeEvent, event),
                        element,
                        shape_thickness_percent=shape_thickness_percent,
                        shape_slide_off_by_one=shape_slide_off_by_one,
                        shape_rounded=shape_rounded,
                    )
                elif name == "AddTldrawShapeEvent":
                    tldraw.parse_add_shape(cast(tldraw.AddShapeEvent, event), element)
                elif name == "ClearPageEvent" or name == "ClearWhiteboardEvent":
                    parse_clear(
                        cast(ClearEvent, event),
                        element,
                        shape_slide_off_by_one=shape_slide_off_by_one,
                    )
                elif name == "DeleteTldrawShapeEvent":
                    tldraw.parse_delete_shape(
                        cast(tldraw.DeleteShapeEvent, event), element
                    )
                elif name == "UndoShapeEvent" or name == "UndoAnnotationEvent":
                    parse_undo(
                        cast(UndoEvent, event),
                        element,
                        shape_slide_off_by_one=shape_slide_off_by_one,
                    )
                elif name == "WhiteboardCursorMoveEvent":
                    parse_whiteboard_cursor(
                        cast(WhiteboardCursorEvent, event),
                        element,
                        tldraw_whiteboard=tldraw_whiteboard,
                    )
                else:
                    # Unknown whiteboard events probably mean recording rendering will be incorrect.
                    raise UnknownEventError(event["name"])

            else:
                # Not interested in events from other modules
                continue

            events.append(event)
        except EventParsingError as e:
            print(e)
        finally:
            element.clear()

    if not have_record_events:
        # Add a fake record start event to the events list
        start_record: RecordEvent = {
            "name": "record",
            "timestamp": Fraction(0, 1000),
            "status": True,
        }
        events.appendleft(start_record)

    return events, last_timestamp, hide_logo, tldraw_whiteboard
