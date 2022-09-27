from math import hypot
from typing import List, Sequence, Tuple

S = Sequence[float]
V = Tuple[float, float]


def add(a: S, b: S) -> V:
    """Add vectors."""
    return (a[0] + b[0], a[1] + b[1])


def sub(a: S, b: S) -> V:
    """Subtract vectors."""
    return (a[0] - b[0], a[1] - b[1])


def vec(a: S, b: S) -> V:
    """Get the vector from vectors A to B."""
    return (b[0] - a[0], b[1] - a[1])


def mul(a: S, n: float) -> V:
    """Vector multiplication by a scalar."""
    return (a[0] * n, a[1] * n)


def div(a: S, n: float) -> V:
    """Vector division by a scalar."""
    return (a[0] / n, a[1] / n)


def per(a: S) -> V:
    """Perpendicular rotation of a vector A."""
    return (a[1], -a[0])


def vlen(a: S) -> float:
    """Length of the vector."""
    return hypot(a[0], a[1])


def uni(a: S) -> V:
    """Get normalized / unit vector."""
    return div(a, vlen(a))


def dist(a: S, b: S) -> float:
    """Dist length from a to b."""
    return hypot(a[1] - b[1], a[0] - b[0])


def med(a: S, b: S) -> V:
    """Mean between two vectors or mid vector between two vectors."""
    return mul(add(a, b), 0.5)


def lrp(a: S, b: S, t: float) -> V:
    """Interpolate vector A to B with a scalar t."""
    return add(a, mul(sub(b, a), t))


def points_between(a: S, b: S, steps: int = 6) -> List[Tuple[float, float, float]]:
    """Get an array of points (with simulated pressure) between two points."""
    points: List[Tuple[float, float, float]] = []
    for i in range(0, steps):
        t = i / (steps - 1)
        k = min(1, 0.5 + abs(0.5 - t))
        points.append((*lrp(a, b, t), k))
    return points
