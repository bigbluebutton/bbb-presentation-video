from fractions import Fraction
import argparse

__all__ = ["events", "renderer"]

from .events import parse_events, DEFAULT_PRESENTATION_POD
from .renderer import Renderer
import os
import sys


DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 720
DEFAULT_RATE = Fraction("24000/1000")
DEFAULT_INPUT = "."
DEFAULT_OUTPUT = "presentation.mkv"


def main():
    # Make stdout unbuffered so we get progress reporting
    class Unbuffered:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            self.stream.write(data)
            self.stream.flush()

        def __getattr__(self, attr):
            return getattr(self.stream, attr)

    sys.stdout = Unbuffered(sys.stdout)

    parser = argparse.ArgumentParser(
        description="Render BigBlueButton events to video", add_help=False
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument(
        "-w",
        "--width",
        metavar="WIDTH",
        type=int,
        help="video width (default: %(default)s)",
        default=DEFAULT_WIDTH,
    )
    parser.add_argument(
        "-h",
        "--height",
        metavar="HEIGHT",
        type=int,
        help="video height (default: %(default)s)",
        default=DEFAULT_HEIGHT,
    )
    parser.add_argument(
        "-r",
        "--framerate",
        metavar="RATE",
        type=Fraction,
        help="video framerate (default: %(default)s)",
        default=DEFAULT_RATE,
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="DIRECTORY",
        type=str,
        help="input directory (default: current working directory)",
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILENAME",
        type=str,
        help="output filename (default: %(default)s)",
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "-s",
        "--start",
        metavar="SECONDS",
        type=Fraction,
        help="generate video for recording section starting at SECONDS",
    )
    parser.add_argument(
        "-e",
        "--end",
        metavar="SECONDS",
        type=Fraction,
        help="generate video for recording section ending at SECONDS",
    )
    parser.add_argument(
        "-p",
        "--pod",
        metavar="POD_ID",
        type=str,
        help="generate video for a specific pod instead of default pod",
        default=DEFAULT_PRESENTATION_POD,
    )

    args = parser.parse_args()

    print(f'Using recording data from "{args.input}"')
    print(f"Video size is {args.width}x{args.height}, framerate {args.framerate}")
    print(f'Outputting video to "{args.output}"')

    print("Parsing events XML...")
    events, length, hide_logo = parse_events(args.input)
    print(
        f"Parsed {len(events)} events, recording length is {float(length)} seconds, the bbb logo will be "
        + "{logo_view_status} for blank frames".format(
            logo_view_status="hidden" if hide_logo else "shown"
        )
    )
    if args.start is not None:
        print(f"Recording section starting at {args.start} seconds")
    if args.end is not None:
        print(f"Recording section ending at {args.end} seconds")

    print("Rendering output video...")
    renderer = Renderer(
        events,
        length,
        args.input,
        args.output,
        args.width,
        args.height,
        args.framerate,
        args.start,
        args.end,
        args.pod,
        hide_logo,
    )

    renderer.render()


if __name__ == "__main__":
    main()
