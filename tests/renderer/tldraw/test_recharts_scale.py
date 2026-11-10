from decimal import Decimal

from bbb_presentation_video.renderer.tldraw.recharts_scale import get_nice_tick_values


def test_get_nice_tick_values_match_recharts() -> None:
    # Reference values produced by recharts-scale 0.4.5 (the version bundled
    # with bbb-playback): getNiceTickValues([0, maximum], 5, false)
    expected = {
        0: [0, 1, 2, 3, 4],
        1: [0, 1, 2, 3, 4],
        2: [0, 1, 2, 3, 4],
        3: [0, 1, 2, 3, 4],
        4: [0, 1, 2, 3, 4],
        5: [0, 2, 4, 6, 8],
        6: [0, 2, 4, 6, 8],
        7: [0, 2, 4, 6, 8],
        8: [0, 2, 4, 6, 8],
        9: [0, 3, 6, 9, 12],
        10: [0, 3, 6, 9, 12],
        11: [0, 3, 6, 9, 12],
        12: [0, 3, 6, 9, 12],
        13: [0, 4, 8, 12, 16],
        20: [0, 5, 10, 15, 20],
        25: [0, 7, 14, 21, 28],
        37: [0, 10, 20, 30, 40],
        50: [0, 15, 30, 45, 60],
        99: [0, 25, 50, 75, 100],
        100: [0, 25, 50, 75, 100],
        101: [0, 30, 60, 90, 120],
        250: [0, 65, 130, 195, 260],
        999: [0, 250, 500, 750, 1000],
        1000: [0, 250, 500, 750, 1000],
    }
    for maximum, ticks in expected.items():
        assert get_nice_tick_values((0, maximum), 5, allow_decimals=False) == [
            Decimal(tick) for tick in ticks
        ]
