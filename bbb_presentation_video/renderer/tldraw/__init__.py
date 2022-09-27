from enum import Enum
from math import cos, floor, hypot, inf, pi, sin
from random import Random
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

import cairo
import gi
import perfect_freehand
from attrs import define, astuple
from cattrs import Converter, structure_attrs_fromdict
from pkg_resources import resource_filename
from sortedcollections import ValueSortedDict

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Pango, PangoCairo

from bbb_presentation_video import events
from bbb_presentation_video.bindings import fontconfig
from bbb_presentation_video.events import Event, Size, tldraw
from bbb_presentation_video.events.helpers import Color, Position, color_blend
from bbb_presentation_video.renderer.presentation import (
    Transform,
    apply_slide_transform,
)
from bbb_presentation_video.renderer.tldraw import easings, vec
from bbb_presentation_video.renderer.utils import perimeter_of_ellipse
from bbb_presentation_video.renderer.whiteboard import BEZIER_CIRCLE_MAGIC

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

CANVAS: Color = Color.from_int(0xFAFAFA)


class SizeStyle(Enum):
    SMALL: str = "small"
    MEDIUM: str = "medium"
    LARGE: str = "large"


STROKE_WIDTHS: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 2.0,
    SizeStyle.MEDIUM: 3.5,
    SizeStyle.LARGE: 5.0,
}

FONT_SIZES: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 28,
    SizeStyle.MEDIUM: 48,
    SizeStyle.LARGE: 96,
}


class ColorStyle(Enum):
    WHITE: str = "white"
    LIGHT_GRAY: str = "lightGray"
    GRAY: str = "gray"
    BLACK: str = "black"
    GREEN: str = "green"
    CYAN: str = "cyan"
    BLUE: str = "blue"
    INDIGO: str = "indigo"
    VIOLET: str = "violet"
    RED: str = "red"
    ORANGE: str = "orange"
    YELLOW: str = "yellow"


STROKES: Dict[ColorStyle, Color] = {
    ColorStyle.WHITE: Color.from_int(0x1D1D1D),
    ColorStyle.LIGHT_GRAY: Color.from_int(0xC6CBD1),
    ColorStyle.GRAY: Color.from_int(0x788492),
    ColorStyle.BLACK: Color.from_int(0x1D1D1D),
    ColorStyle.GREEN: Color.from_int(0x36B24D),
    ColorStyle.CYAN: Color.from_int(0x0E98AD),
    ColorStyle.BLUE: Color.from_int(0x1C7ED6),
    ColorStyle.INDIGO: Color.from_int(0x4263EB),
    ColorStyle.VIOLET: Color.from_int(0x7746F1),
    ColorStyle.RED: Color.from_int(0xFF2133),
    ColorStyle.ORANGE: Color.from_int(0xFF9433),
    ColorStyle.YELLOW: Color.from_int(0xFFC936),
}

FILLS: Dict[ColorStyle, Color] = dict(
    [
        (
            k,
            color_blend(v, CANVAS, 0.82)
            if k is not ColorStyle.WHITE
            else Color.from_int(0xFEFEFE),
        )
        for k, v in STROKES.items()
    ]
)


class DashStyle(Enum):
    DRAW: str = "draw"
    SOLID: str = "solid"
    DASHED: str = "dashed"
    DOTTED: str = "dotted"


class FontStyle(Enum):
    SCRIPT: str = "script"
    SANS: str = "sans"
    ERIF: str = "erif"  # SIC
    SERIF: str = "serif"  # In case they fix the spelling
    MONO: str = "mono"


FONT_FACES: Dict[FontStyle, str] = {
    FontStyle.SCRIPT: "Caveat Brush",
    FontStyle.SANS: "Source Sans Pro",
    FontStyle.ERIF: "Crimson Pro",
    FontStyle.SERIF: "Crimson Pro",
    FontStyle.MONO: "Source Code Pro",
}


class AlignStyle(Enum):
    START: str = "start"
    MIDDLE: str = "middle"
    END: str = "end"
    JUSTIFY: str = "justify"


@define
class Style:
    color: ColorStyle = ColorStyle.BLACK
    size: SizeStyle = SizeStyle.SMALL
    dash: DashStyle = DashStyle.DRAW
    isFilled: bool = False
    scale: float = 1
    font: FontStyle = FontStyle.SCRIPT
    textAlign: AlignStyle = AlignStyle.MIDDLE


@define
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: float
    height: float


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

    def bend_point(self) -> Tuple[float, float]:
        start_point = astuple(self.handles.start.point)
        end_point = astuple(self.handles.end.point)

        dist = vec.dist(start_point, end_point)
        mid_point = vec.med(start_point, end_point)
        bend_dist = (dist / 2) * self.bend
        u = vec.uni(vec.vec(start_point, end_point))

        point: Tuple[float, float]
        if bend_dist < 10:
            point = mid_point
        else:
            point = vec.add(mid_point, vec.mul(vec.per(u), bend_dist))
        return point


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


def shape_sort_key(shape: BaseShape) -> float:
    return shape.childIndex


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


def get_bounds_from_points(
    points: Sequence[Union[Tuple[float, float], Tuple[float, float, float]]]
) -> Bounds:
    min_x = min_y = inf
    max_x = max_y = -inf

    if len(points) == 0:
        min_x = min_y = max_x = max_y = 0

    for point in points:
        x = point[0]
        y = point[1]
        min_x = min(x, min_x)
        min_y = min(y, min_y)
        max_x = max(x, max_x)
        max_y = max(y, max_y)

    return Bounds(min_x, min_y, max_x, max_y, max_x - min_x, max_y - min_y)


def get_perfect_dash_props(
    length: float,
    stroke_width: float,
    style: DashStyle,
    snap: int = 1,
    outset: bool = True,
    length_ratio: float = 2,
) -> Tuple[List[float], float]:

    if style is DashStyle.DASHED:
        dash_length = stroke_width * length_ratio
        ratio = 1
        offset = dash_length / 2 if outset else 0
    elif style is DashStyle.DOTTED:
        dash_length = stroke_width / 100
        ratio = 100
        offset = 0
    else:
        return ([], 0)

    dashes = floor(length / dash_length / (2 * ratio))
    dashes -= dashes % snap
    dashes = max(dashes, 4)

    gap_length = max(
        dash_length,
        (length - dashes * dash_length) / (dashes if outset else dashes - 1),
    )

    return ([dash_length, gap_length], offset)


def apply_shape_rotation(ctx: cairo.Context, shape: RotatableShapeProto) -> None:
    x = shape.size.width / 2
    y = shape.size.height / 2
    ctx.translate(x, y)
    ctx.rotate(shape.rotation)
    ctx.translate(-x, -y)


def draw_stroke_points(
    points: Sequence[Tuple[float, float]], stroke_width: float, is_complete: bool
) -> List[perfect_freehand.types.StrokePoint]:
    return perfect_freehand.get_stroke_points(
        points,
        size=1 + stroke_width * 1.5,
        streamline=0.65,
        last=is_complete,
    )


def rectangle_stroke_points(
    id: str, shape: RectangleShape
) -> List[perfect_freehand.types.StrokePoint]:
    random = Random(id)
    print(f"\tRandom state: {random.random()}")
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    # Corners
    variation = sw * 0.75
    tl = (
        sw / 2 + random.uniform(-variation, variation),
        sw / 2 + random.uniform(-variation, variation),
    )
    tr = (
        w - sw / 2 + random.uniform(-variation, variation),
        sw / 2 + random.uniform(-variation, variation),
    )
    br = (
        w - sw / 2 + random.uniform(-variation, variation),
        h - sw / 2 + random.uniform(-variation, variation),
    )
    bl = (
        sw / 2 + random.uniform(-variation, variation),
        h - sw / 2 + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 4)

    # Corner radii
    rx = min(w / 4, sw * 2)
    ry = min(h / 4, sw / 2)

    # Number of points per side
    px = max(8, floor(w / 16))
    py = max(8, floor(h / 16))

    # Inset each line by the corner radii and let the freehand algo
    # interpolate points for the corners.
    lines = [
        vec.points_between(vec.add(tl, (rx, 0)), vec.sub(tr, (rx, 0)), px),
        vec.points_between(vec.add(tr, (0, ry)), vec.sub(br, (0, ry)), py),
        vec.points_between(vec.sub(br, (rx, 0)), vec.add(bl, (rx, 0)), px),
        vec.points_between(vec.sub(bl, (0, ry)), vec.add(tl, (0, ry)), py),
    ]
    lines = lines[rm:] + lines[0:rm]

    # For the final points, include the first half of the first line again,
    # so that the line wraps around and avoids ending on a sharp corner.
    # This has a bit of finesse and magic—if you change the points_between
    # function, then you'll likely need to change this one too.
    points: List[Tuple[float, float, float]] = [
        *lines[0],
        *lines[1],
        *lines[2],
        *lines[3],
        *lines[0],
    ]

    return perfect_freehand.get_stroke_points(
        points[5 : floor(len(lines[0]) / -2) + 3],
        size=sw,
        streamline=0.3,
        last=True,
    )


def triangle_stroke_points(
    id: str, shape: TriangleShape
) -> List[perfect_freehand.types.StrokePoint]:
    random = Random(id)
    print(f"\tRandom state: {random.random()}")
    sw = STROKE_WIDTHS[shape.style.size]

    # Dimensions
    w = max(0, shape.size.width)
    h = max(0, shape.size.height)

    # Corners
    variation = sw * 0.75
    t = (
        w / 2 + random.uniform(-variation, variation),
        random.uniform(-variation, variation),
    )
    br = (
        w + random.uniform(-variation, variation),
        h + random.uniform(-variation, variation),
    )
    bl = (
        random.uniform(-variation, variation),
        h + random.uniform(-variation, variation),
    )

    # Which side to start drawing first
    rm = random.randrange(0, 3)

    lines = [
        vec.points_between(t, br, 32),
        vec.points_between(br, bl, 32),
        vec.points_between(bl, t, 32),
    ]
    lines = lines[rm:] + lines[0:rm]

    points: List[Tuple[float, float, float]] = [
        *lines[0],
        *lines[1],
        *lines[2],
        *lines[0],
    ]

    return perfect_freehand.get_stroke_points(
        points, size=sw, streamline=0.3, last=True
    )


def ellipse_stroke_points(
    id: str, shape: EllipseShape
) -> Tuple[List[perfect_freehand.types.StrokePoint], float]:
    stroke_width = STROKE_WIDTHS[shape.style.size]
    random = Random(id)
    variation = stroke_width * 2
    rx = shape.radius[0] + random.uniform(-variation, variation)
    ry = shape.radius[1] + random.uniform(-variation, variation)
    perimeter = perimeter_of_ellipse(rx, ry)
    points: List[Tuple[float, float, float]] = []
    start = pi + pi + random.uniform(-1, 1)
    extra = random.random()
    count = int(max(16, perimeter / 10))
    for i in range(0, count):
        t = easings.ease_in_out_sine(i / (count + 1))
        rads = start * 2 + pi * (2 + extra) * t
        c = cos(rads)
        s = sin(rads)
        points.append(
            (
                rx * c + shape.radius[0],
                ry * s + shape.radius[1],
                t + random.random(),
            )
        )

    return (
        perfect_freehand.get_stroke_points(
            points, size=2 + stroke_width * 2, streamline=0
        ),
        perimeter,
    )


def freehand_draw_easing(t: float) -> float:
    return sin(t * pi) / 2


def bezier_quad_to_cube(
    qp0: Tuple[float, float], qp1: Tuple[float, float], qp2: Tuple[float, float]
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    return (
        vec.add(qp0, vec.mul(vec.sub(qp1, qp0), 2 / 3)),
        vec.add(qp2, vec.mul(vec.sub(qp1, qp2), 2 / 3)),
    )


def draw_smooth_path(
    ctx: cairo.Context, points: Sequence[Tuple[float, float]], closed: bool = True
) -> None:
    """Turn an array of points into a path of quadratic curves."""

    if len(points) < 1:
        return

    prev_point = points[0]
    if closed:
        prev_mid = vec.med(points[-1], prev_point)
    else:
        prev_mid = prev_point
    ctx.move_to(prev_mid[0], prev_mid[1])
    for point in points[1:]:
        mid = vec.med(prev_point, point)
        print(
            f"Prev Mid: {prev_mid}, Prev Point: {prev_point}, Mid: {mid}, Point: {point}"
        )

        # Cairo can't render quadratic curves directly, need to convert to cubic curves.
        cp1, cp2 = bezier_quad_to_cube(prev_mid, prev_point, mid)
        ctx.curve_to(cp1[0], cp1[1], cp2[0], cp2[1], mid[0], mid[1])
        prev_point = point
        prev_mid = mid

    if closed:
        point = points[0]
        mid = vec.med(prev_point, point)
    else:
        point = points[-1]
        mid = point

    print(f"Prev Mid: {prev_mid}, Prev Point: {prev_point}, Mid: {mid}, Point: {point}")

    cp1, cp2 = bezier_quad_to_cube(prev_mid, prev_point, mid)
    ctx.curve_to(cp1[0], cp1[1], cp2[0], cp2[1], mid[0], mid[1])

    if closed:
        ctx.close_path()


def draw_smooth_stroke_point_path(
    ctx: cairo.Context,
    points: Sequence[perfect_freehand.types.StrokePoint],
    closed: bool = True,
) -> None:
    outline_points = list(map(lambda p: p["point"], points))
    draw_smooth_path(ctx, outline_points, closed)


class TldrawRenderer:
    """Render tldraw whiteboard shapes"""

    ctx: cairo.Context
    """The cairo rendering context for drawing the whiteboard."""

    presentation: Optional[str] = None
    """The current presentation."""

    slide: Optional[int] = None
    """The current slide."""

    presentation_slide: Dict[str, int]
    """The last shown slide on a given presentation."""

    shapes: Dict[
        str, Dict[int, ValueSortedDict]
    ]  # should be ValueSortedDict[str, Shape]
    """The list of shapes, organized by presentation then slide."""

    shapes_changed: bool = False
    """Whether there have been changes to rendered shapes since the last frame."""

    transform: Transform
    """The current transform."""

    pattern: Optional[cairo.Pattern] = None
    """Cached rendered shapes for the current transform."""

    def __init__(self, ctx: cairo.Context, transform: Transform):
        self.ctx = ctx
        self.presentation_slide = {}
        self.shapes = {}
        self.transform = transform

        fontconfig.app_font_add_dir(resource_filename(__name__, "fonts"))

    def ensure_shape_structure(self, presentation: str, slide: int) -> None:
        try:
            p = self.shapes[presentation]
        except KeyError:
            p = self.shapes[presentation] = {}
        try:
            p[slide]
        except KeyError:
            p[slide] = ValueSortedDict(shape_sort_key)

    def presentation_event(self, event: events.PresentationEvent) -> None:
        presentation = event["presentation"]
        if self.presentation == presentation:
            print("\tTldraw: presentation did not change")
            return

        self.presentation = presentation
        self.slide = self.presentation_slide.get(presentation, 0)
        self.shapes_changed = True
        print(f"\tTldraw: presentation: {self.presentation}, slide: {self.slide}")

    def slide_event(self, event: events.SlideEvent) -> None:
        presentation = self.presentation
        if presentation is None:
            print(
                f"\tTldraw: ignoring slide update since current presentation is not known"
            )
            return

        slide = event["slide"]
        if self.slide == slide:
            print("\tTldraw: slide did not change")
            return

        self.slide = slide
        self.presentation_slide[presentation] = slide
        self.shapes_changed = True
        print(f"\tTldraw: presentation: {presentation}, slide: {slide}")

    def add_shape_event(self, event: tldraw.AddShapeEvent) -> None:
        presentation = event["presentation"]
        slide = event["slide"]
        id = event["id"]
        data = event["data"]

        if data["type"] == "image":
            print(f"\tTldraw: ignoring image shape type: {id}")
            return

        print(repr(data))

        shape: Shape = converter.structure(data, Shape)  # type: ignore
        print(repr(shape))

        self.ensure_shape_structure(presentation, slide)
        self.shapes[presentation][slide][id] = shape
        self.shapes_changed = True
        print(
            f"\tTldraw: added shape: {id}, presentation: {presentation}, slide: {slide}, type: {shape.__class__.__name__}"
        )

    def delete_shape_event(self, event: tldraw.DeleteShapeEvent) -> None:
        id = event["id"]
        presentation = event["presentation"]
        slide = event["slide"]
        try:
            del self.shapes[presentation][slide][id]
        except KeyError:
            return
        self.shapes_changed = True
        print(
            f"\tTldraw: deleted shape: {id}, presentation: {presentation}, slide: {slide}"
        )

    def update(self, event: Event) -> None:
        if event["name"] == "presentation":
            self.presentation_event(cast(events.PresentationEvent, event))
        elif event["name"] == "slide":
            self.slide_event(cast(events.SlideEvent, event))
        elif event["name"] == "tldraw.add_shape":
            self.add_shape_event(cast(tldraw.AddShapeEvent, event))
        elif event["name"] == "tldraw.delete_shape":
            self.delete_shape_event(cast(tldraw.DeleteShapeEvent, event))

    def finalize_draw(self, id: str, shape: DrawShape) -> None:
        print(f"\tTldraw: Finalizing Draw: {id}")

        ctx = self.ctx
        apply_shape_rotation(ctx, shape)

        style = shape.style
        points = shape.points
        stroke_color = STROKES[style.color]
        stroke_width = STROKE_WIDTHS[style.size]

        bounds = shape.cached_bounds
        if bounds is None:
            bounds = shape.cached_bounds = get_bounds_from_points(points)

        if bounds.width <= stroke_width / 2 and bounds.height <= stroke_width < 2:
            # Shape is too small, draw a circle
            ctx.arc(0, 0, 1 + stroke_width, 0, 2 * pi)
            ctx.set_source_rgb(*stroke_color)
            ctx.fill_preserve()
            ctx.set_line_cap(cairo.LineCap.ROUND)
            ctx.set_line_join(cairo.LineJoin.ROUND)
            ctx.set_line_width(stroke_width / 2)
            ctx.stroke()
            return

        stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None

        should_fill = (
            style.isFilled
            and len(shape.points) > 3
            and vec.dist(points[0], points[-1]) < stroke_width * 2
        )

        if should_fill:
            # Shape is configured to be filled, and is fillable
            cached_path = shape.cached_path
            if cached_path is not None:
                ctx.append_path(cached_path)
            else:
                stroke_points = draw_stroke_points(
                    points, stroke_width, shape.isComplete
                )
                draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
                shape.cached_path = ctx.copy_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        if style.dash is DashStyle.DRAW:
            # Smoothed freehand drawing style
            cached_outline_path = shape.cached_outline_path
            if cached_outline_path is not None:
                ctx.append_path(cached_outline_path)
            else:
                if stroke_points is None:
                    stroke_points = draw_stroke_points(
                        points, stroke_width, shape.isComplete
                    )
                stroke_outline_points = perfect_freehand.get_stroke_outline_points(
                    stroke_points,
                    size=1 + stroke_width * 1.5,
                    thinning=0.65,
                    smoothing=0.65,
                    simulate_pressure=True,
                    last=shape.isComplete,
                    easing=freehand_draw_easing,
                )
                draw_smooth_path(ctx, stroke_outline_points)
                shape.cached_outline_path = ctx.copy_path()
            ctx.set_source_rgb(*stroke_color)
            ctx.fill_preserve()
            ctx.set_line_cap(cairo.LineCap.ROUND)
            ctx.set_line_join(cairo.LineJoin.ROUND)
            ctx.set_line_width(stroke_width / 2)
            ctx.stroke()
            return

        elif style.dash is DashStyle.DOTTED:
            ctx.set_dash([0, stroke_width * 4])
        elif style.dash is DashStyle.DASHED:
            ctx.set_dash([stroke_width * 4, stroke_width * 4])

        # Normal stroked path, possibly with dash or dot pattern
        cached_path = shape.cached_path
        if cached_path is not None:
            ctx.append_path(cached_path)
        else:
            stroke_points = draw_stroke_points(points, stroke_width, shape.isComplete)
            draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
            shape.cached_path = ctx.copy_path()
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_line_width(1 + stroke_width * 1.5)
        ctx.set_source_rgb(*stroke_color)
        ctx.stroke()

    def finalize_draw_rectangle(self, id: str, shape: RectangleShape) -> None:
        ctx = self.ctx
        style = shape.style

        stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None

        if style.isFilled:
            cached_path = shape.cached_path
            if cached_path is not None:
                ctx.append_path(cached_path)
            else:
                stroke_points = rectangle_stroke_points(id, shape)
                draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
                shape.cached_path = ctx.copy_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        cached_outline_path = shape.cached_outline_path
        if cached_outline_path is not None:
            ctx.append_path(cached_outline_path)
        else:
            if stroke_points is None:
                stroke_points = rectangle_stroke_points(id, shape)
            stroke_outline_points = perfect_freehand.get_stroke_outline_points(
                stroke_points,
                size=STROKE_WIDTHS[style.size],
                thinning=0.65,
                smoothing=1,
                simulate_pressure=False,
                last=True,
            )
            draw_smooth_path(ctx, stroke_outline_points, closed=True)
            shape.cached_outline_path = ctx.copy_path()

        ctx.set_source_rgb(*STROKES[style.color])
        ctx.fill_preserve()
        ctx.set_line_width(STROKE_WIDTHS[style.size])
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.stroke()

    def finalize_dash_rectangle(self, shape: RectangleShape) -> None:
        ctx = self.ctx
        style = shape.style
        stroke_width = STROKE_WIDTHS[style.size] * 1.618

        sw = 1 + stroke_width
        w = max(0, shape.size.width - sw / 2)
        h = max(0, shape.size.height - sw / 2)

        if style.isFilled:
            ctx.move_to(sw / 2, sw / 2)
            ctx.line_to(w, sw / 2)
            ctx.line_to(w, h)
            ctx.line_to(sw / 2, h)
            ctx.close_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        strokes = [
            ((sw / 2, sw / 2), (w, sw / 2), w - sw / 2),
            ((w, sw / 2), (w, h), h - sw / 2),
            ((w, h), (sw / 2, h), w - sw / 2),
            ((sw / 2, h), (sw / 2, sw / 2), h - sw / 2),
        ]
        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_source_rgb(*STROKES[style.color])
        for start, end, length in strokes:
            dash_array, dash_offset = get_perfect_dash_props(
                length, stroke_width, style.dash
            )
            ctx.move_to(*start)
            ctx.line_to(*end)
            ctx.set_dash(dash_array, dash_offset)
            ctx.stroke()

    def finalize_rectangle(self, id: str, shape: RectangleShape) -> None:
        print(f"\tTldraw: Finalizing Rectangle: {id}")

        ctx = self.ctx
        apply_shape_rotation(ctx, shape)

        style = shape.style

        if style.dash is DashStyle.DRAW:
            self.finalize_draw_rectangle(id, shape)
        else:
            self.finalize_dash_rectangle(shape)

        self.finalize_label(shape)

    def finalize_draw_triangle(self, id: str, shape: TriangleShape) -> None:
        ctx = self.ctx
        style = shape.style

        stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None

        if style.isFilled:
            cached_path = shape.cached_path
            if cached_path is not None:
                ctx.append_path(cached_path)
            else:
                stroke_points = triangle_stroke_points(id, shape)
                draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
                shape.cached_path = ctx.copy_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        cached_outline_path = shape.cached_outline_path
        if cached_outline_path is not None:
            ctx.append_path(cached_outline_path)
        else:
            if stroke_points is None:
                stroke_points = triangle_stroke_points(id, shape)
            stroke_outline_points = perfect_freehand.get_stroke_outline_points(
                stroke_points,
                size=STROKE_WIDTHS[style.size],
                thinning=0.65,
                smoothing=1,
                simulate_pressure=False,
                last=True,
            )
            draw_smooth_path(ctx, stroke_outline_points, closed=True)
            shape.cached_outline_path = ctx.copy_path()

        ctx.set_source_rgb(*STROKES[style.color])
        ctx.fill_preserve()
        ctx.set_line_width(STROKE_WIDTHS[style.size])
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.stroke()

    def finalize_dash_triangle(self, shape: TriangleShape) -> None:
        ctx = self.ctx
        style = shape.style
        stroke_width = STROKE_WIDTHS[style.size] * 1.618

        sw = 1 + stroke_width
        w = max(0, shape.size.width - sw / 2)
        h = max(0, shape.size.height - sw / 2)

        side_width = hypot(w / 2, h)

        if style.isFilled:
            ctx.move_to(w / 2, 0)
            ctx.line_to(w, h)
            ctx.line_to(0, h)
            ctx.close_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        strokes = [
            ((w / 2, 0), (w, h), side_width),
            ((w, h), (0, h), w),
            ((0, h), (w / 2, 0), side_width),
        ]
        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_source_rgb(*STROKES[style.color])
        for start, end, length in strokes:
            dash_array, dash_offset = get_perfect_dash_props(
                length, stroke_width, style.dash
            )
            ctx.move_to(*start)
            ctx.line_to(*end)
            ctx.set_dash(dash_array, dash_offset)
            ctx.stroke()

    def finalize_triangle(self, id: str, shape: TriangleShape) -> None:
        print(f"\tTldraw: Finalizing Triangle: {id}")

        ctx = self.ctx
        apply_shape_rotation(ctx, shape)

        style = shape.style

        if style.dash is DashStyle.DRAW:
            self.finalize_draw_triangle(id, shape)
        else:
            self.finalize_dash_triangle(shape)

        self.finalize_label(shape)

    def finalize_draw_ellipse(self, id: str, shape: EllipseShape) -> None:
        ctx = self.ctx
        style = shape.style

        stroke_points: Optional[List[perfect_freehand.types.StrokePoint]] = None
        perimeter: Optional[float]

        if style.isFilled:
            cached_path = shape.cached_path
            if cached_path is not None:
                ctx.append_path(cached_path)
            else:
                stroke_points, perimeter = ellipse_stroke_points(id, shape)
                draw_smooth_stroke_point_path(ctx, stroke_points, closed=False)
                shape.cached_path = ctx.copy_path()
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill()

        cached_outline_path = shape.cached_outline_path
        if cached_outline_path is not None:
            ctx.append_path(cached_outline_path)
        else:
            if stroke_points is None or perimeter is None:
                stroke_points, perimeter = ellipse_stroke_points(id, shape)
            stroke_outline_points = perfect_freehand.get_stroke_outline_points(
                stroke_points,
                size=2 + STROKE_WIDTHS[style.size] * 2,
                thinning=0.618,
                taper_end=perimeter / 8,
                taper_start=perimeter / 12,
                simulate_pressure=True,
            )
            draw_smooth_path(ctx, stroke_outline_points, closed=True)
            shape.cached_outline_path = ctx.copy_path()

        ctx.set_source_rgb(*STROKES[style.color])
        ctx.fill_preserve()
        ctx.set_line_width(STROKE_WIDTHS[style.size])
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.stroke()

    def finalize_dash_ellipse(self, shape: EllipseShape) -> None:
        ctx = self.ctx
        style = shape.style
        stroke_width = STROKE_WIDTHS[style.size] * 1.618
        radius_x = shape.radius[0]
        radius_y = shape.radius[1]

        sw = 1 + stroke_width
        rx = max(0, radius_x - sw / 2)
        ry = max(0, radius_y - sw / 2)
        perimeter = perimeter_of_ellipse(rx, ry)
        dash_array, dash_offset = get_perfect_dash_props(
            perimeter * 2 if perimeter < 64 else perimeter,
            stroke_width,
            style.dash,
            snap=4,
        )

        # Draw a bezier approximation to the ellipse. Cairo's arc function
        # doesn't deal well with degenerate (0-height/width) ellipses because
        # of the scaling required.
        ctx.translate(radius_x, radius_y)  # math is easier from center of ellipse
        ctx.move_to(-rx, 0)
        ctx.curve_to(
            -rx, -ry * BEZIER_CIRCLE_MAGIC, -rx * BEZIER_CIRCLE_MAGIC, -ry, 0, -ry
        )
        ctx.curve_to(
            rx * BEZIER_CIRCLE_MAGIC, -ry, rx, -ry * BEZIER_CIRCLE_MAGIC, rx, 0
        )
        ctx.curve_to(rx, ry * BEZIER_CIRCLE_MAGIC, rx * BEZIER_CIRCLE_MAGIC, ry, 0, ry)
        ctx.curve_to(
            -rx * BEZIER_CIRCLE_MAGIC, ry, -rx, ry * BEZIER_CIRCLE_MAGIC, -rx, 0
        )
        ctx.close_path()

        if style.isFilled:
            ctx.set_source_rgb(*FILLS[style.color])
            ctx.fill_preserve()

        ctx.set_dash(dash_array, dash_offset)
        ctx.set_line_width(sw)
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.set_source_rgb(*STROKES[style.color])
        ctx.stroke()

    def finalize_ellipse(self, id: str, shape: EllipseShape) -> None:
        print(f"\tTldraw: Finalizing Ellipse: {id}")

        ctx = self.ctx
        apply_shape_rotation(ctx, shape)

        style = shape.style

        if style.dash is DashStyle.DRAW:
            self.finalize_draw_ellipse(id, shape)
        else:
            self.finalize_dash_ellipse(shape)

        self.finalize_label(shape)

    def finalize_arrow(self, shape: ArrowShape) -> None:
        ...

    def finalize_label(self, shape: LabelledShapeProto) -> None:
        if shape.label is None or shape.label == "":
            return

        print(f"\tTldraw: Finalizing Label")

        ctx = self.ctx

        style = shape.style

        pctx = PangoCairo.create_context(ctx)

        font = Pango.FontDescription()
        font.set_family(FONT_FACES[FontStyle.SCRIPT])
        font.set_absolute_size(FONT_SIZES[style.size] * style.scale * Pango.SCALE)

        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_GRAY)
        fo.set_hint_metrics(cairo.HINT_METRICS_ON)
        fo.set_hint_style(cairo.HINT_STYLE_NONE)
        PangoCairo.context_set_font_options(pctx, fo)

        layout = Pango.Layout(pctx)
        layout.set_auto_dir(True)
        layout.set_font_description(font)
        layout.set_width(int(shape.size.width * Pango.SCALE))
        layout.set_height(int(shape.size.height * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_alignment(Pango.Alignment.CENTER)

        layout.set_text(shape.label, -1)

        (_, layout_height) = layout.get_pixel_size()
        height_offset = (shape.size.height - layout_height) / 2
        ctx.translate(0, height_offset)

        ctx.set_source_rgb(*STROKES[style.color])

        PangoCairo.show_layout(ctx, layout)

    def finalize_text(self, id: str, shape: TextShape) -> None:
        print(f"\tTldraw: Finalizing Text: {id}")

        ctx = self.ctx
        apply_shape_rotation(ctx, shape)

        style = shape.style

        pctx = PangoCairo.create_context(ctx)

        font = Pango.FontDescription()
        font.set_family(FONT_FACES[style.font])
        font.set_absolute_size(FONT_SIZES[style.size] * style.scale * Pango.SCALE)

        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_GRAY)
        fo.set_hint_metrics(cairo.HINT_METRICS_ON)
        fo.set_hint_style(cairo.HINT_STYLE_NONE)
        PangoCairo.context_set_font_options(pctx, fo)

        layout = Pango.Layout(pctx)
        layout.set_auto_dir(True)
        layout.set_font_description(font)
        layout.set_width(int(shape.size.width * Pango.SCALE))
        layout.set_height(int(shape.size.height * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        if style.textAlign == AlignStyle.START:
            layout.set_alignment(Pango.Alignment.LEFT)
        elif style.textAlign == AlignStyle.MIDDLE:
            layout.set_alignment(Pango.Alignment.CENTER)
        elif style.textAlign == AlignStyle.END:
            layout.set_alignment(Pango.Alignment.RIGHT)
        elif style.textAlign == AlignStyle.JUSTIFY:
            layout.set_alignment(Pango.Alignment.LEFT)
            layout.set_justify(True)

        layout.set_text(shape.text, -1)

        ctx.set_source_rgb(*STROKES[style.color])

        PangoCairo.show_layout(ctx, layout)

    def finalize_frame(self, transform: Transform) -> bool:
        if not self.shapes_changed and self.transform == transform:
            return False
        self.transform = transform
        presentation = self.presentation
        slide = self.slide
        if (
            presentation is None
            or slide is None
            or not presentation in self.shapes
            or not slide in self.shapes[presentation]
        ):
            self.pattern = None
            return False

        shapes = self.shapes[presentation][slide]
        print(f"\tTldraw: Rendering {len(shapes)} shapes.")

        ctx = self.ctx
        ctx.push_group()

        apply_slide_transform(ctx, transform)

        for id, s in shapes.items():
            shape = cast(Shape, s)

            ctx.save()

            ctx.translate(*shape.point)

            if isinstance(shape, DrawShape):
                self.finalize_draw(id, shape)
            elif isinstance(shape, RectangleShape):
                self.finalize_rectangle(id, shape)
            elif isinstance(shape, TriangleShape):
                self.finalize_triangle(id, shape)
            elif isinstance(shape, EllipseShape):
                self.finalize_ellipse(id, shape)
            elif isinstance(shape, ArrowShape):
                self.finalize_arrow(shape)
            elif isinstance(shape, TextShape):
                self.finalize_text(id, shape)
            elif isinstance(shape, GroupShape):
                # Nothing to do? All group-related updates seem to be propagated to the
                # individual shapes in the group.
                pass
            else:
                print(f"\tTldraw: Don't know how to render {shape}")

            ctx.restore()

        self.pattern = ctx.pop_group()
        self.shapes_changed = False

        return True

    def render(self) -> None:
        if self.pattern is not None:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
