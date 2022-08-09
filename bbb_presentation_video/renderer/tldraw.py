from enum import Enum
from lib2to3.pgen2.token import OP
from attrs import define
from cattrs import Converter, structure_attrs_fromdict, override
from cattrs.gen import make_dict_structure_fn
from typing import (
    Iterable,
    Protocol,
    Type,
    Union,
    cast,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)
from sortedcollections import ValueSortedDict

import cairo
from bbb_presentation_video import events

from bbb_presentation_video.events import Event, Size, tldraw
from bbb_presentation_video.events.helpers import Position, Color
from bbb_presentation_video.renderer.presentation import (
    Transform,
    apply_slide_transform,
)


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


class SizeStyle(Enum):
    SMALL: str = "small"
    MEDIUM: str = "medium"
    LARGE: str = "large"


STROKE_WIDTHS: Dict[SizeStyle, float] = {
    SizeStyle.SMALL: 2.0,
    SizeStyle.MEDIUM: 3.5,
    SizeStyle.LARGE: 5.0,
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


COLORS: Dict[ColorStyle, Color] = {
    ColorStyle.WHITE: Color.from_int(0xF0F1F3),
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


class DashStyle(Enum):
    DRAW: str = "draw"
    SOLID: str = "solid"
    DASHED: str = "dashed"
    DOTTED: str = "dotted"


class FontStyle(Enum):
    SCRIPT: str = "script"
    SANS: str = "sans"
    SERIF: str = "erif"  # SIC
    MONO: str = "mono"


FONT_FACES: Dict[FontStyle, str] = {
    FontStyle.SCRIPT: "Caveat Brush",
    FontStyle.SANS: "Source Sans Pro",
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
    color: ColorStyle
    size: SizeStyle
    dash: DashStyle
    isFilled: Optional[bool] = None
    scale: Optional[float] = None
    font: Optional[FontStyle] = None
    textAlign: Optional[AlignStyle] = None


@define
class BaseShape:
    style: Style
    parentId: str
    childIndex: float
    point: Position


@define
class DrawShape(BaseShape):
    points: List[Position]
    isComplete: bool


@define
class RectangleShape(BaseShape):
    size: Size
    label: Optional[str]
    labelPoint: Position


@define
class EllipseShape(BaseShape):
    radius: Tuple[float, float]
    label: Optional[str]
    labelPoint: Position


@define
class TriangleShape(BaseShape):
    size: Size
    label: Optional[str]
    labelPoint: Position


@define
class ArrowShape(BaseShape):
    size: Size
    label: Optional[str]
    labelPoint: Position
    rotation: float
    bend: float


@define
class TextShape(BaseShape):
    text: str


@define
class GroupShape(BaseShape):
    children: List[str]


@define
class StickyShape(BaseShape):
    text: str


@define
class ImageShape(BaseShape):
    assetId: str


def shape_sort_key(shape: BaseShape) -> float:
    print(repr(shape))
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
    ImageShape,
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
    elif type == "image":
        return converter.structure(o, ImageShape)
    else:
        raise Exception(f"Unhandled Tldraw shape type: {type}")


converter.register_structure_hook(Shape, shape_structure_hook)


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
        print(repr(data))

        shape: Shape = converter.structure(data, Shape)
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

    def finalize_draw(self, shape: DrawShape) -> None:
        ctx = self.ctx

        # TODO: this needs to be rendered with perfect-freehand
        style = shape.style
        ctx.set_source_rgb(*COLORS[style.color])
        ctx.set_line_width(STROKE_WIDTHS[style.size])

        # TODO: dashes

        points = shape.points

        print(f"\tTldraw: Finalizing Draw {repr(points)}")

        # TODO: once perfect freehand is done, will want to cache this path.
        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_line_join(cairo.LineJoin.ROUND)
        ctx.move_to(*points[0])
        if len(points) > 1:
            for point in points[1:-1]:
                ctx.line_to(*point)
        else:
            ctx.line_to(*points[0])

        ctx.stroke()

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

        for shape in shapes.values():
            ctx.save()

            ctx.translate(*shape.point)

            if isinstance(shape, DrawShape):
                self.finalize_draw(shape)
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
