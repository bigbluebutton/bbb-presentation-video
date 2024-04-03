# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import sys
from fractions import Fraction
from importlib.metadata import PackageNotFoundError, metadata
from os import path
from typing import IO, Any, cast

__all__ = ["events", "renderer"]

from bbb_presentation_video.events import DEFAULT_PRESENTATION_POD, parse_events
from bbb_presentation_video.renderer import Codec, Renderer

DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 720
DEFAULT_RATE = Fraction("24000/1000")
DEFAULT_INPUT = "."
DEFAULT_OUTPUT = "presentation.mkv"


def main() -> None:
    # Make stdout unbuffered so we get progress reporting
    class Unbuffered:
        stream: IO[str]

        def __init__(self, stream: IO[str]):
            self.stream = stream

        def write(self, data: str) -> int:
            ret = self.stream.write(data)
            self.stream.flush()
            return ret

        def __getattr__(self, attr: str) -> Any:
            return getattr(self.stream, attr)

    sys.stdout = cast(Any, Unbuffered(sys.stdout))

    parser = argparse.ArgumentParser(
        description="Render BigBlueButton presentation/whiteboard events to video",
        add_help=False,
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
        "-c",
        "--codec",
        metavar="CODEC",
        type=Codec,
        help="output file video codec (default: %(default)s)",
        default="vp9",
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

    try:
        bpv_metadata = metadata(__package__)
        print(f'{bpv_metadata["Name"]} version {bpv_metadata["Version"]}')
    except PackageNotFoundError:
        print(
            f"{path.basename(sys.argv[0])} development version running from source directory"
        )

    print(f'Using recording data from "{args.input}"')
    print(
        f"Video size is {args.width}x{args.height}, framerate {args.framerate}, codec {args.codec.value}"
    )
    print(f'Outputting video to "{args.output}"')

    print("Parsing events XML...")
    events = parse_events(args.input)
    if events.length is None:
        print(f"Could not determine recording length - cannot generate video.")
        exit(1)

    print(f"Parsed {len(events.events)} events")
    print(f"Recording length is {float(events.length):.3f} seconds")
    print(
        f"The bbb logo will be {'hidden' if events.hide_logo else 'shown'} for blank frames"
    )
    if args.start is not None:
        print(f"Recording section starting at {args.start} seconds")
    if args.end is not None:
        print(f"Recording section ending at {args.end} seconds")

    print("Rendering output video...")
    renderer = Renderer(
        events,
        args.input,
        args.output,
        args.width,
        args.height,
        args.framerate,
        args.codec,
        args.start,
        args.end,
        args.pod,
    )

    renderer.render()


if __name__ == "__main__":
    main()
