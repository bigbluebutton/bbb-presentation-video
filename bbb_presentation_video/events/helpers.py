from attrs import define
from typing import Iterator, Optional, Type, TypeVar
from lxml import etree
from bbb_presentation_video.events.errors import EventParsingError

_ColorSelf = TypeVar("_ColorSelf", bound="Color")


@define
class Color:
    r: float
    g: float
    b: float
    a: Optional[float] = None

    @classmethod
    def from_int(
        cls: Type[_ColorSelf], i: int, a: Optional[float] = None
    ) -> _ColorSelf:
        return cls(
            r=((i & 0xFF0000) >> 16) / 255.0,
            g=((i & 0x00FF00) >> 8) / 255.0,
            b=((i & 0x0000FF)) / 255.0,
            a=a,
        )

    def __iter__(self) -> Iterator[float]:
        yield self.r
        yield self.g
        yield self.b
        if self.a is not None:
            yield self.a


@define
class Position:
    x: float
    y: float

    def __str__(self) -> str:
        return f"[{self.x:.3f},{self.y:.3f}]"

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __mul__(self, other: float) -> "Position":
        return Position(self.x * other, self.y * other)


def xml_subelement_opt(element: etree._Element, name: str) -> Optional[str]:
    subelement = element.find(name)
    return subelement.text if subelement is not None else None


def xml_subelement(element: etree._Element, eventname: str, name: str) -> str:
    text = xml_subelement_opt(element, name)
    if text is None:
        raise EventParsingError(eventname, f"Missing XML subelement: {name}")
    return text


def xml_subelement_shape_slide(
    element: etree._Element, shape_slide_off_by_one: bool
) -> Optional[int]:
    slide = xml_subelement_opt(element, "slide")
    if slide is not None:
        s = int(slide)
        if shape_slide_off_by_one:
            return s - 1
        else:
            return s
    return None
