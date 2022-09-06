from math import pi, sqrt
from typing import Iterator, TypeVar


def perimeter_of_ellipse(rx: float, ry: float) -> float:
    """Find the approximate perimeter of an ellipse."""
    h = (rx - ry) ** 2 / (rx + ry) ** 2
    return pi * (rx + ry) * (1 + (3 * h) / (10 + sqrt(4 - 3 * h)))
