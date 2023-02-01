# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
from collections import deque
from enum import Enum
from fractions import Fraction
from queue import Queue
from subprocess import PIPE, CalledProcessError, Popen
from typing import Deque, Iterable, Optional, cast

import cairo

from bbb_presentation_video import events
from bbb_presentation_video.events import Event, PerPodEvent, RecordEvent, Size
from bbb_presentation_video.events.helpers import Color
from bbb_presentation_video.renderer.cursor import CursorRenderer
from bbb_presentation_video.renderer.presentation import PresentationRenderer
from bbb_presentation_video.renderer.tldraw import TldrawRenderer
from bbb_presentation_video.renderer.whiteboard import ShapesRenderer

DRAWING_BG = Color.from_int(0xE2E8ED)


class Codec(Enum):
    H264 = "h264"
    VP9 = "vp9"


class Encoder:
    queue: "Queue[Optional[bytearray]]"
    ret_queue: "Queue[bytearray]"

    def __init__(
        self, output: str, width: int, height: int, framerate: Fraction, codec: Codec
    ):
        self.output = output
        self.width = width
        self.height = height
        self.framerate = framerate
        self.codec = codec

        self.queue = Queue()
        self.ret_queue = Queue()
        for x in range(0, 3):
            self.ret_queue.put(bytearray(width * height * 4))

        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def put(self, data: bytes) -> None:
        buf = self.ret_queue.get()
        buf[:] = data
        self.queue.put(buf)

    def join(self) -> None:
        # This is a sentinal value to tell the writing thread to exit
        self.queue.put(None)
        self.thread.join()

    def run(self) -> None:
        if self.codec == Codec.H264:
            codec_opts = ["-c:v", "libx264", "-qp", "0", "-preset", "ultrafast"]
        elif self.codec == Codec.VP9:
            codec_opts = [
                "-c:v",
                "libvpx-vp9",
                "-deadline",
                "realtime",
                "-cpu-used",
                "8",
                "-lossless",
                "1",
                "-row-mt",
                "1",
            ]
        # Launch the video encoder
        # Note that the hardcoded 'bgr0' here is only applicable in
        # little-endian!
        ffmpeg_cmdline = [
            "ffmpeg",
            "-y",
            "-nostats",
            "-v",
            "warning",
            "-f",
            "rawvideo",
            "-pixel_format",
            "bgr0",
            "-video_size",
            f"{self.width:d}x{self.height:d}",
            "-framerate",
            str(self.framerate),
            "-i",
            "-",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            f"mpdecimate=max={int(round(self.framerate)):d}:hi=1:lo=1:frac=1",
            *codec_opts,
            "-threads",
            "2",
            "-g",
            str(round(self.framerate) * 10),
            "-f",
            "matroska",
            self.output,
        ]

        ffmpeg = Popen(ffmpeg_cmdline, stdin=PIPE, stdout=PIPE, close_fds=True)
        assert ffmpeg.stdout is not None and ffmpeg.stdin is not None
        ffmpeg.stdout.close()

        while True:
            buf = self.queue.get()
            if buf is None:
                break

            ffmpeg.stdin.write(buf)

            self.ret_queue.put(buf)

        ffmpeg.stdin.close()
        ffmpeg.wait()

        if ffmpeg.returncode != 0:
            raise CalledProcessError(returncode=ffmpeg.returncode, cmd=ffmpeg_cmdline)


class Renderer:
    events: Deque[Event]
    length: Fraction
    input: str
    output: str
    width: int
    height: int
    framerate: Fraction
    codec: Codec
    pod_id: str
    hide_logo: bool
    tldraw_whiteboard: bool

    frame: int
    framestep: Fraction
    pts: Fraction
    recording: bool

    def __init__(
        self,
        events: Iterable[Event],
        length: Fraction,
        input: str,
        output: str,
        width: int,
        height: int,
        framerate: Fraction,
        codec: Codec,
        start_time: Fraction,
        end_time: Fraction,
        pod_id: str,
        hide_logo: bool,
        tldraw_whiteboard: bool,
    ):
        # The events get modified, so make a copy of the queue
        self.events = deque(events)
        self.length = length
        self.input = input
        self.output = output
        self.width = width
        self.height = height
        self.framerate = framerate
        self.codec = codec
        self.pod_id = pod_id
        self.hide_logo = hide_logo
        self.tldraw_whiteboard = tldraw_whiteboard

        # Current video position state
        self.frame = 1
        self.framestep = 1 / framerate
        self.pts = Fraction(0)
        self.recording = False

        # Only the section of recording within the time range of start_time
        # through end_time will be included in the final video
        if start_time is not None:
            self.start_time = start_time
        else:
            self.start_time = 0
        if end_time is not None and end_time < length:
            self.length = end_time

        # Cairo rendering context
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.width, self.height)
        self.ctx = cairo.Context(self.surface)

        # Set up font rendering options
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.ANTIALIAS_GRAY)
        font_options.set_hint_style(cairo.HINT_STYLE_NONE)
        self.ctx.set_font_options(font_options)

    def update_record(self, event: RecordEvent) -> None:
        if self.recording != event["status"]:
            self.recording = event["status"]
            print(f"\tRenderer: recording: {self.recording}")

    def render(self) -> None:
        cursor = CursorRenderer(
            self.ctx,
            Size(self.width, self.height),
            tldraw_whiteboard=self.tldraw_whiteboard,
        )
        presentation = PresentationRenderer(
            self.ctx,
            self.input,
            Size(self.width, self.height),
            self.hide_logo,
            tldraw_whiteboard=self.tldraw_whiteboard,
        )
        shapes = ShapesRenderer(self.ctx, presentation.transform)
        tldraw = TldrawRenderer(self.ctx, presentation.transform)

        encoder = Encoder(
            self.output, self.width, self.height, self.framerate, self.codec
        )

        presentation_changed = True
        shapes_changed = False
        cursor_changed = False
        recording_changed = False
        while self.pts < self.length:
            event_ts = Fraction(0)
            while True:
                if len(self.events) == 0:
                    break

                event = self.events[0]
                event_ts = event["timestamp"]
                if event_ts > self.pts:
                    break

                self.events.popleft()

                name = event["name"]
                print(f"{float(event['timestamp']):012.6f} {event['name']}")

                # Skip events that are for a different pod
                if name in ["pan_zoom", "presentation", "slide", "presenter"]:
                    pod_event = cast(PerPodEvent, event)
                    if pod_event["pod_id"] != self.pod_id:
                        print(f"\tskipping event for pod {pod_event['pod_id']}")
                        continue

                tldraw.update(event)

                if name == "cursor":
                    cursor.update_cursor(cast(events.CursorEvent, event))
                elif name == "cursor_v2":
                    cursor.update_cursor_v2(cast(events.WhiteboardCursorEvent, event))
                elif name == "pan_zoom":
                    presentation.update_pan_zoom(cast(events.PanZoomEvent, event))
                elif name == "presentation":
                    presentation_event = cast(events.PresentationEvent, event)
                    presentation.update_presentation(presentation_event)
                    shapes.update_presentation(presentation_event)
                    cursor.update_presentation(presentation_event)
                elif name == "slide":
                    slide_event = cast(events.SlideEvent, event)
                    presentation.update_slide(slide_event)
                    shapes.update_slide(slide_event)
                    cursor.update_slide(slide_event)
                elif name == "shape":
                    shape_event = cast(events.ShapeEvent, event)
                    shapes.update_shape(shape_event)
                    cursor.update_shape(shape_event)
                elif name == "undo":
                    shapes.update_undo(cast(events.UndoEvent, event))
                elif name == "clear":
                    shapes.update_clear(cast(events.ClearEvent, event))
                elif name == "record":
                    self.update_record(cast(events.RecordEvent, event))
                    recording_changed = True
                elif name == "presenter":
                    cursor.update_presenter(cast(events.PresenterEvent, event))
                elif name == "join":
                    cursor.update_join(cast(events.JoinEvent, event))
                elif name == "left":
                    cursor.update_left(cast(events.LeftEvent, event))
                elif (
                    name == "tldraw.add_shape"
                    or name == "tldraw.delete_shape"
                    or name == "tldraw.camera"
                ):
                    pass
                else:
                    print("\tdon't know how to handle this event")

            if self.recording and self.pts >= self.start_time:
                presentation_changed = presentation.finalize_frame()
                shapes_changed = shapes.finalize_frame(presentation.transform)
                tldraw_changed = tldraw.finalize_frame(presentation.transform)
                cursor_changed = cursor.finalize_frame(presentation.transform)

                if (
                    presentation_changed
                    or shapes_changed
                    or tldraw_changed
                    or cursor_changed
                ):
                    # Composite the frame

                    # Base background color
                    ctx = self.ctx
                    ctx.save()
                    ctx.set_source_rgb(*DRAWING_BG)
                    ctx.paint()
                    ctx.restore()

                    # Presentation
                    presentation.render()

                    # Shapes
                    shapes.render()
                    tldraw.render()

                    # Cursor
                    cursor.render()

                    recording_changed = True

                if recording_changed:
                    print(f"-- {float(self.pts):012.6f} frame {self.frame}")
                # Output a frame
                self.surface.flush()
                encoder.put(bytearray(self.surface.get_data()))

            self.frame += 1
            self.pts += self.framestep

            presentation_changed = False
            shapes_changed = False
            cursor_changed = False
            recording_changed = False

        encoder.join()
