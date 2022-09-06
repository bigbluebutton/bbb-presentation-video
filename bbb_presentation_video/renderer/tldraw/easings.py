from math import cos, pi


def ease_in_out_sine(t: float) -> float:
    return -(cos(pi * t) - 1) / 2
