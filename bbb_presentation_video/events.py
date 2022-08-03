from attrs import define
from lxml import etree
from collections import deque
from fractions import Fraction
from enum import Enum
from distutils.version import StrictVersion
from typing import NamedTuple, Optional, TypeVar
import json

MAGIC_MYSTERY_NUMBER = 2.0
DEFAULT_PRESENTATION_POD = "DEFAULT_PRESENTATION_POD"


@define
class Position:
    x: float
    y: float

    def __str__(self):
        return f"[{self.x:.3f},{self.y:.3f}]"

    def __mul__(self, other: float):
        return Position(self.x * other, self.y * other)


@define
class Size:
    width: float
    height: float

    def __str__(self):
        return f"{self.width:.3f}x{self.height:.3f}"

    def __mul__(self, other: float):
        return Size(self.width * other, self.height * other)


ColorSelf = TypeVar("ColorSelf", bound="Color")


@define
class Color:
    r: float
    g: float
    b: float
    a: Optional[float] = None

    @classmethod
    def from_int(cls: type[ColorSelf], i: int, a: Optional[float] = None) -> ColorSelf:
        return cls(
            r=((i & 0xFF0000) >> 16) / 255.0,
            g=((i & 0x00FF00) >> 8) / 255.0,
            b=((i & 0x0000FF)) / 255.0,
            a=a,
        )

    def __iter__(self):
        yield self.r
        yield self.g
        yield self.b
        if self.a is not None:
            yield self.a


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


class EventParsingError(Exception):
    event: dict

    def __init__(self, event: dict):
        self.event = event

    def __str__(self):
        return f"Failed to parse event {self.event}"


class UnknownEventError(EventParsingError):
    def __str__(self):
        return f"Unknown event {self.event}"


class UnknownShapeError(EventParsingError):
    shape: str

    def __init__(self, event: dict, shape: str):
        super().__init__(event)
        self.shape = shape

    def __str__(self):
        return f"Unknown shape '{self.shape}' in {self.event}"


class InvalidShapeError(EventParsingError):
    shape: str
    status: str
    reason: str

    def __init__(self, event: dict, shape: str, status: str, reason: str):
        super().__init__(event)
        self.shape = shape
        self.status = status
        self.reason = reason

    def __str__(self):
        return f"Shape {self.shape} in {self.event} with status {self.status} is invalid: {self.reason}"


class ShapeNoDataPointsError(InvalidShapeError):
    def __init__(self, event: dict, shape: str, status: str):
        super().__init__(event, shape, status, "no dataPoints")


def parse_cursor(event: dict, element: etree._Element):
    x_offset = element.find("xOffset")
    y_offset = element.find("yOffset")
    if x_offset is None or y_offset is None:
        raise EventParsingError(event)

    x = float(x_offset.text or 0)
    y = float(y_offset.text or 0)
    if x < 0 or x > 1 or y < 0 or y > 1:
        cursor = None
    else:
        cursor = Position(x, y)

    event["cursor"] = cursor
    event["name"] = "cursor"


def parse_whiteboard_cursor(event, element):
    x_offset = element.find("xOffset")
    y_offset = element.find("yOffset")
    user_id = element.find("userId")
    presentation = element.find("presentation")
    pageNumber = element.find("pageNumber")

    if presentation is not None:
        event["presentation"] = presentation.text
    if pageNumber is not None:
        event["slide"] = int(pageNumber.text)

    cursor = Position(float(x_offset.text) / 100, float(y_offset.text) / 100)
    if cursor.x < 0 or cursor.x > 1 or cursor.y < 0 or cursor.y > 1:
        cursor = None
    event["cursor"] = cursor
    event["user_id"] = user_id.text
    event["name"] = "cursor_v2"


def parse_pan_zoom(event, element):
    x_offset = element.find("xOffset")
    y_offset = element.find("yOffset")
    width_ratio = element.find("widthRatio")
    height_ratio = element.find("heightRatio")
    pod_id = element.find("podId")

    # Workaround a bug where BBB can return 'NaN' in the values
    if x_offset.text == "NaN" or y_offset.text == "NaN":
        event["pan"] = Position(0.0, 0.0)
    else:
        event["pan"] = Position(
            float(x_offset.text) * MAGIC_MYSTERY_NUMBER / 100,
            float(y_offset.text) * MAGIC_MYSTERY_NUMBER / 100,
        )
    if width_ratio.text == "NaN" or height_ratio.text == "NaN":
        event["zoom"] = Size(1.0, 1.0)
    else:
        event["zoom"] = Size(
            float(width_ratio.text) / 100, float(height_ratio.text) / 100
        )
    # Workaround a bug where BBB can return a width or height ratio of 0,
    # which is nonsensical and causes divide-by-zero errors.
    # It can also return values less than zero, I dunno what's up with that.
    if event["zoom"].width <= 0 or event["zoom"].height <= 0:
        event["zoom"] = Size(1.0, 1.0)

    if pod_id is None:
        event["pod_id"] = DEFAULT_PRESENTATION_POD
    else:
        event["pod_id"] = pod_id.text

    event["name"] = "pan_zoom"


def parse_slide(event, element):
    slide = element.find("slide")
    pod_id = element.find("podId")

    event["slide"] = int(slide.text)

    if pod_id is None:
        event["pod_id"] = DEFAULT_PRESENTATION_POD
    else:
        event["pod_id"] = pod_id.text

    event["name"] = "slide"


def parse_presentation(event, element):
    presentation_name = element.find("presentationName")
    pod_id = element.find("podId")

    event["presentation"] = presentation_name.text

    if pod_id is None:
        event["pod_id"] = DEFAULT_PRESENTATION_POD
    else:
        event["pod_id"] = pod_id.text

    event["name"] = "presentation"


def parse_shape(
    event, element, shape_thickness_percent, shape_slide_off_by_one, shape_rounded
):
    # Common attributes for all shapes
    id = element.find("id")
    type = element.find("type")
    presentation = element.find("presentation")
    pageNumber = element.find("pageNumber")
    data_points = element.find("dataPoints")
    status = element.find("status")
    user_id = element.find("userId")

    if id is not None:
        event["shape_id"] = id.text
    else:
        event["shape_id"] = None
    if presentation is not None:
        event["presentation"] = presentation.text
    if pageNumber is not None:
        event["slide"] = int(pageNumber.text)
        if shape_slide_off_by_one:
            event["slide"] -= 1
    event["shape_type"] = shape_type = type.text
    if status is not None:
        event["shape_status"] = ShapeStatus[status.text]
    if user_id is not None:
        event["user_id"] = user_id.text

    # We have to ignore draw events with an empty dataPoints. An example of
    # where this happens is in the DRAW_END event for the pencil tool when
    # server-side smoothing failed - the final event has no points, and we're
    # expected to use the existing shape as-is
    if data_points.text is None:
        raise ShapeNoDataPointsError(event["name"], shape_type, event["shape_status"])

    # The 'dataPoints' element contains a list of alternating X and Y
    # coordinates. Collapse them into a collection of Positions
    points = data_points.text.split(",")
    event["points"] = deque()
    points_iter = iter(points)
    while True:
        try:
            event["points"].append(
                Position(float(next(points_iter)) / 100, float(next(points_iter)) / 100)
            )
        except StopIteration:
            break

    if shape_type in ["pencil", "rectangle", "ellipse", "triangle", "line"]:
        # These shapes share a bunch of attributes
        color = element.find("color")
        thickness = element.find("thickness")
        event["color"] = Color.from_int(int(color.text))
        if shape_thickness_percent:
            event["thickness_ratio"] = float(thickness.text) / 100
        else:
            event["thickness"] = float(thickness.text)
        # Pencil is always rounded; other shapes use flag
        event["rounded"] = shape_rounded or shape_type == "pencil"

        # Some extra attributes for special shapes
        if shape_type == "rectangle":
            square = element.find("square")
            if square is not None:
                event["square"] = square.text == "true"
            else:
                event["square"] = False
        elif shape_type == "ellipse":
            circle = element.find("circle")
            if circle is not None:
                event["circle"] = circle.text == "true"
            else:
                event["circle"] = False
        elif shape_type == "pencil":
            commands = element.find("commands")
            if commands is not None:
                event["commands"] = [
                    PencilCommand(int(x)) for x in commands.text.split(",")
                ]

    elif shape_type == "poll_result":
        num_responders = element.find("num_responders")
        num_respondents = element.find("num_respondents")
        result = element.find("result")

        event["num_responders"] = int(num_responders.text)
        event["num_respondents"] = int(num_respondents.text)
        event["result"] = json.loads(result.text)

    elif shape_type == "text":
        # Note that we don't need the X and Y; they're duplicated from
        # the dataPoints  list.
        text_box_height = element.find("textBoxHeight")
        text_box_width = element.find("textBoxWidth")
        font_size = element.find("fontSize")
        font_color = element.find("fontColor")
        calced_font_size = element.find("calcedFontSize")
        text = element.find("text")

        if calced_font_size is None:
            raise InvalidShapeError(
                event["name"],
                shape_type,
                event["shape_status"],
                "Missing calcedFontSize",
            )

        event["width"] = float(text_box_width.text) / 100
        event["height"] = float(text_box_height.text) / 100
        event["font_color"] = Color.from_int(int(font_color.text))
        event["font_size"] = float(font_size.text)
        event["calced_font_size"] = float(calced_font_size.text) / 100
        event["text"] = text.text or ""
    else:
        raise UnknownShapeError(event["name"], shape_type)
    event["name"] = "shape"


def parse_undo(event, element, shape_slide_off_by_one):
    presentation = element.find("presentation")
    pageNumber = element.find("pageNumber")
    user_id = element.find("userId")
    shape_id = element.find("shapeId")

    event["name"] = "undo"
    if presentation is not None:
        event["presentation"] = presentation.text
    if pageNumber is not None:
        event["slide"] = int(pageNumber.text)
        if shape_slide_off_by_one:
            event["slide"] -= 1
    if user_id is not None:
        event["user_id"] = user_id.text
    if shape_id is not None:
        event["shape_id"] = shape_id.text


def parse_clear(event, element, shape_slide_off_by_one):
    presentation = element.find("presentation")
    pageNumber = element.find("pageNumber")
    user_id = element.find("userId")
    full_clear = element.find("fullClear")

    event["name"] = "clear"
    if presentation is not None:
        event["presentation"] = presentation.text
    if pageNumber is not None:
        event["slide"] = int(pageNumber.text)
        if shape_slide_off_by_one:
            event["slide"] -= 1
    if user_id is not None:
        event["user_id"] = user_id.text
    if full_clear is not None:
        event["full_clear"] = full_clear.text == "true"


def parse_record(event, element):
    status = element.find("status")
    event["name"] = "record"
    event["status"] = status.text == "true"


def parse_presenter(event, element):
    user_id = element.find("userid")
    name = element.find("name")
    event["user_id"] = user_id.text
    event["pod_id"] = DEFAULT_PRESENTATION_POD
    event["name"] = "presenter"


def parse_pod_presenter(event, element):
    next_presenter_id = element.find("nextPresenterId")
    pod_id = element.find("podId")
    event["user_id"] = next_presenter_id.text
    event["pod_id"] = pod_id.text
    event["name"] = "presenter"


def parse_join(event, element):
    user_id = element.find("userId")
    external_user_id = element.find("externalUserId")
    role = element.find("role")
    name = element.find("name")
    event["user_id"] = user_id.text
    event["user_name"] = name.text
    event["name"] = "join"


def parse_left(event, element):
    user_id = element.find("userId")
    event["user_id"] = user_id.text
    event["name"] = "left"


def parse_events(directory="."):
    start_time = None
    last_timestamp = None
    have_record_events = False
    events = deque()

    root = etree.parse(f"{directory}/events.xml")
    root_e = root.getroot()
    print(f"Events: bbb_version: {root_e.get('bbb_version')}")

    use_pod_presenter = False
    shape_thickness_percent = False
    shape_slide_off_by_one = True
    shape_rounded = True
    try:
        bbb_version = StrictVersion(root_e.get("bbb_version"))
        use_pod_presenter = bbb_version >= StrictVersion("2.1")
        shape_thickness_percent = bbb_version >= StrictVersion("2.0")
        shape_slide_off_by_one = not (bbb_version >= StrictVersion("0.9.0"))
        shape_rounded = not (bbb_version >= StrictVersion("2.0"))
    except AttributeError:
        pass

    print(f"Events: shape_thickness_percent: {shape_thickness_percent}")
    print(f"Events: shape_slide_off_by_one: {shape_slide_off_by_one}")

    hide_logo = root.find("metadata").get("bn-rec-hide-logo", "false") == "true"

    for element in root.iter("event"):
        try:
            event = {}

            # Convert timestamps to be in seconds from recording start
            timestamp = int(element.attrib["timestamp"])
            if not start_time:
                start_time = timestamp
            timestamp = Fraction(timestamp - start_time, 1000)

            # Save the timestamp of last event as recording length
            last_timestamp = timestamp

            # Only need events from these modules
            if not element.attrib["module"] in [
                "PRESENTATION",
                "WHITEBOARD",
                "PARTICIPANT",
            ]:
                continue

            event["name"] = name = element.attrib["eventname"]
            event["timestamp"] = timestamp

            # PRESENTATION
            if name == "CursorMoveEvent":
                parse_cursor(event, element)
            elif name == "WhiteboardCursorMoveEvent":
                parse_whiteboard_cursor(event, element)
            elif name == "ResizeAndMoveSlideEvent":
                parse_pan_zoom(event, element)
            elif name == "GotoSlideEvent":
                parse_slide(event, element)
            elif name == "SharePresentationEvent":
                parse_presentation(event, element)
            elif name == "SetPresenterInPodEvent":
                parse_pod_presenter(event, element)
            # WHITEBOARD
            elif name == "AddShapeEvent" or name == "ModifyTextEvent":
                parse_shape(
                    event,
                    element,
                    shape_thickness_percent,
                    shape_slide_off_by_one,
                    shape_rounded,
                )
            elif name == "UndoShapeEvent" or name == "UndoAnnotationEvent":
                parse_undo(event, element, shape_slide_off_by_one)
            elif name == "ClearPageEvent" or name == "ClearWhiteboardEvent":
                parse_clear(event, element, shape_slide_off_by_one)
            # PARTICIPANT
            elif name == "RecordStatusEvent":
                parse_record(event, element)
                have_record_events = True
            elif name == "AssignPresenterEvent":
                if use_pod_presenter:
                    continue
                else:
                    parse_presenter(event, element)
            elif name == "ParticipantJoinEvent":
                parse_join(event, element)
            elif name == "ParticipantLeftEvent":
                parse_left(event, element)
            # These events are not used; from progress reports when
            # generating slides.
            elif name == "ConversionCompletedEvent":
                continue
            elif name == "GenerateSlideEvent":
                continue
            # We're only interested in the one PARTICIPANT event, ignore others
            elif element.attrib["module"] == "PARTICIPANT":
                continue
            else:
                raise UnknownEventError(name)

            events.append(event)
        except EventParsingError as e:
            print(e)
        finally:
            element.clear()

    if not have_record_events:
        # Add a fake record start event to the events list
        event = {"name": "record", "timestamp": Fraction(0, 1000), "status": True}
        events.appendleft(event)

    return events, last_timestamp, hide_logo
