# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import (
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import attr
from lxml import etree

from bbb_presentation_video.events.errors import EventParsingError

ColorSelf = TypeVar("ColorSelf", bound="Color")


@attr.s(order=False, slots=True, auto_attribs=True)
class Color:
    r: float
    g: float
    b: float
    a: Optional[float] = None

    @classmethod
    def from_int(cls: Type[ColorSelf], i: int, a: Optional[float] = None) -> ColorSelf:
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


def color_blend(a: Color, b: Color, t: float) -> Color:
    return Color(
        r=(a.r + t * (b.r - a.r)),
        g=(a.g + t * (b.g - a.g)),
        b=(a.b + t * (b.b - a.b)),
    )


PositionSelf = TypeVar("PositionSelf", bound="Position")


@attr.s(order=False, slots=True, auto_attribs=True, init=False)
class Position(Sequence[float]):
    x: float
    y: float

    @overload
    def __init__(self, iterable: Iterable[float], /) -> None:
        ...

    @overload
    def __init__(self, x: float, y: float) -> None:
        ...

    def __init__(
        self, x: Union[Iterable[float], float], y: Optional[float] = None
    ) -> None:
        if isinstance(x, Iterable):
            i = iter(x)
            self.x = next(i)
            self.y = next(i)
        else:
            self.x = x
            self.y = cast(float, y)

    def __str__(self) -> str:
        return f"[{self.x:.3f},{self.y:.3f}]"

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __add__(self: PositionSelf, other: Position) -> PositionSelf:
        return self.__class__(self.x + other.x, self.y + other.y)

    def __mul__(self: PositionSelf, other: float) -> PositionSelf:
        return self.__class__(self.x * other, self.y * other)

    def __truediv__(self: PositionSelf, other: float) -> PositionSelf:
        return self.__class__(self.x / other, self.y / other)

    @overload
    def __getitem__(self, index: int) -> float:
        ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[float]:
        ...

    def __getitem__(self, index: Union[int, slice]) -> Union[float, Sequence[float]]:
        return (self.x, self.y)[index]

    def __len__(self) -> int:
        return 2


SizeSelf = TypeVar("SizeSelf", bound="Size")


@attr.s(order=False, slots=True, auto_attribs=True, init=False)
class Size(Sequence[float]):
    width: float
    height: float

    @overload
    def __init__(self, iterable: Iterable[float], /) -> None:
        ...

    @overload
    def __init__(self, width: float, height: float) -> None:
        ...

    def __init__(
        self, width: Union[Iterable[float], float], height: Optional[float] = None
    ) -> None:
        if isinstance(width, Iterable):
            i = iter(width)
            self.width = next(i)
            self.height = next(i)
        else:
            self.width = width
            self.height = cast(float, height)

    def __str__(self) -> str:
        return f"{self.width:.3f}x{self.height:.3f}"

    def __iter__(self) -> Iterator[float]:
        yield self.width
        yield self.height

    def __mul__(self: SizeSelf, other: float) -> SizeSelf:
        return self.__class__(self.width * other, self.height * other)

    def __truediv__(self: SizeSelf, other: float) -> SizeSelf:
        return self.__class__(self.width / other, self.height / other)

    @overload
    def __getitem__(self, index: int) -> float:
        ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[float]:
        ...

    def __getitem__(self, index: Union[int, slice]) -> Union[float, Sequence[float]]:
        return (self.width, self.height)[index]

    def __len__(self) -> int:
        return 2


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
    slide = xml_subelement_opt(element, "pageNumber")
    if slide is not None:
        s = int(slide)
        if shape_slide_off_by_one:
            return s - 1
        else:
            return s
    return None
