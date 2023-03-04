# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import atexit
from contextlib import ExitStack
from enum import Enum
from importlib import resources
from math import ceil, floor
from os import PathLike, fspath, path
from typing import Any, Dict, Generic, Optional, TypeVar, Union

import attr
import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")
gi.require_version("Poppler", "0.18")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Poppler

from bbb_presentation_video import events
from bbb_presentation_video.events.helpers import Position, Size


class ImageType(Enum):
    MISSING = 0
    PDF = 1
    IMAGE = 2


TYPE_MAP = {
    "PDF": ImageType.PDF,
    "pdf": ImageType.PDF,
    "PNG": ImageType.IMAGE,
    "png": ImageType.IMAGE,
    "JPG": ImageType.IMAGE,
    "jpg": ImageType.IMAGE,
    "JPEG": ImageType.IMAGE,
    "jpeg": ImageType.IMAGE,
}

__logo_file_manager = ExitStack()
atexit.register(__logo_file_manager.close)
LOGO_FILE = __logo_file_manager.enter_context(
    resources.path(__package__, "bbb_logo.pdf")
)
LOGO_TYPE = ImageType.PDF

# The size of the scaled coordinate system for drawing on slides
DRAWING_SIZE = 1200

# The size of the scaled coordinate system for tldraw whiteboard
# https://github.com/bigbluebutton/bigbluebutton/blob/v2.6.0-rc.4/bigbluebutton-html5/imports/api/slides/server/helpers.js
TLDRAW_DRAWING_SIZE = Size(2048, 1536)


@attr.s(order=False, slots=True, auto_attribs=True)
class Transform(object):
    padding: Size
    scale: float
    size: Size
    pos: Position
    shapes_scale: float
    shapes_size: Size


CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


def apply_slide_transform(ctx: cairo.Context[CairoSomeSurface], t: Transform) -> None:
    ctx.translate(t.padding.width, t.padding.height)
    ctx.scale(t.scale, t.scale)
    ctx.rectangle(0, 0, t.size.width, t.size.height)
    ctx.clip()
    ctx.translate(-t.pos.x, -t.pos.y)


def apply_shapes_transform(ctx: cairo.Context[CairoSomeSurface], t: Transform) -> Size:
    apply_slide_transform(ctx, t)
    ctx.scale(t.shapes_scale, t.shapes_scale)
    return t.shapes_size


class PresentationRenderer(Generic[CairoSomeSurface]):
    ctx: cairo.Context[CairoSomeSurface]
    directory: str
    size: Size
    hide_logo: bool

    presentation: Optional[str]
    presentation_slide: Dict[str, int]
    slide: int
    pan: Position
    zoom: Size

    presentation_changed: bool
    slide_changed: bool
    pan_zoom_changed: bool
    tldraw_whiteboard: bool

    filename: Optional[Union[str, bytes, PathLike[Any]]]
    filetype: ImageType
    source: Optional[Union[Poppler.Document, GdkPixbuf.Pixbuf]]
    page: Optional[Union[Poppler.Page, GdkPixbuf.Pixbuf]]
    page_size: Optional[Size]
    pattern: Optional[cairo.Pattern]

    def __init__(
        self,
        ctx: cairo.Context[CairoSomeSurface],
        directory: str,
        size: Size,
        hide_logo: bool,
        tldraw_whiteboard: bool,
    ):
        self.ctx = ctx
        self.directory = directory
        self.size = size
        self.hide_logo = hide_logo
        self.tldraw_whiteboard = tldraw_whiteboard

        self.presentation = None
        self.presentation_slide = {}
        self.slide = 0
        self.pan = Position(-0.0, -0.0)
        self.zoom = Size(1.0, 1.0)

        self.presentation_changed = True
        self.slide_changed = False
        self.pan_zoom_changed = False

        self.filename = None
        self.filetype = ImageType.MISSING
        self.source = None
        self.page = None
        self.page_size = None
        self.pattern = None

        # Initial transform is mostly-valid, but useless
        self.trans = Transform(
            padding=Size(0.0, 0.0),
            scale=1.0,
            size=self.size,
            pos=Position(-0.0, -0.0),
            shapes_scale=1.0,
            shapes_size=TLDRAW_DRAWING_SIZE
            if self.tldraw_whiteboard
            else Size(DRAWING_SIZE, DRAWING_SIZE),
        )

    @property
    def transform(self) -> Transform:
        return self.trans

    def print_transform(self) -> None:
        print(f"\tPresentation: padding: {self.trans.padding}")
        print(
            f"\tPresentation: slide size: {self.trans.size}, "
            f"scale: {self.trans.scale:.6f}, position: {self.trans.pos}]"
        )
        print(
            f"\tPresentation: slide scaled size: {self.trans.size * self.trans.scale}"
        )
        print(
            f"\tPresentation: shapes size: {self.trans.shapes_size}, "
            f"scale: {self.trans.shapes_scale:.6f}"
        )

    def update_presentation(self, event: events.PresentationEvent) -> None:
        if self.presentation == event["presentation"]:
            print("\tPresentation: presentation did not change")
            return
        self.presentation = event["presentation"]
        self.presentation_changed = True
        # Restore the last viewed page from this presentation
        self.slide = self.presentation_slide.get(self.presentation, 0)
        # Pan and zoom resets when a presentation is shared
        self.pan = Position(0.0, 0.0)
        self.zoom = Size(1.0, 1.0)
        self.pan_zoom_changed = True
        print(f"\tPresentation: presentation: {self.presentation}")
        print(f"\tPresentation: slide: {self.slide}")

    def update_slide(self, event: events.SlideEvent) -> None:
        if self.slide == event["slide"]:
            print("\tPresentation: slide did not change")
            return
        self.slide = event["slide"]
        if self.presentation is not None:
            self.presentation_slide[self.presentation] = self.slide
        self.slide_changed = True
        print(f"\tPresentation: slide: {self.slide}")

    def update_pan_zoom(self, event: events.PanZoomEvent) -> None:
        if self.pan == event["pan"] and self.zoom == event["zoom"]:
            print("\tPresentation: pan/zoom did not change")
            return
        self.pan = event["pan"]
        self.zoom = event["zoom"]
        self.pan_zoom_changed = True
        print(f"\tPresentation: pan: {self.pan} zoom: {self.zoom}")

    def finalize_frame(self) -> bool:
        needs_render = False

        if self.presentation_changed or self.source is None:
            needs_render = True
            # Find the presentation file and determine its file type
            if self.presentation is None and not self.hide_logo:
                self.filename = LOGO_FILE
                self.filetype = LOGO_TYPE
            else:
                self.filename = None
                self.filetype = ImageType.MISSING
                if self.presentation is not None:
                    for extension in TYPE_MAP:
                        filename = f"{self.directory}/presentation/{self.presentation}/{self.presentation}.{extension}"
                        if path.exists(filename):
                            self.filename = filename
                            self.filetype = TYPE_MAP[extension]
                            break
            print(f"\tPresentation: filename: {self.filename}, type: {self.filetype}")

            # Load the source for the new presentation
            if self.filetype is ImageType.IMAGE:
                assert self.filename is not None
                try:
                    self.source = GdkPixbuf.Pixbuf.new_from_file(fspath(self.filename))
                except GLib.Error as error:
                    print(f"Failed to read image: {error}")
                    self.presentation = None
                    self.filetype = ImageType.MISSING
            elif self.filetype is ImageType.PDF:
                assert self.filename is not None
                try:
                    gfile = Gio.File.new_for_path(fspath(self.filename))
                    self.source = Poppler.Document.new_from_gfile(gfile, None, None)
                except GLib.Error as error:
                    print(f"Failed to read pdf: {error}")
                    self.presentation = None
                    self.filetype = ImageType.MISSING

        if self.slide_changed or needs_render:
            needs_render = True
            # Load the correct page
            if self.filetype is ImageType.IMAGE:
                assert isinstance(self.source, GdkPixbuf.Pixbuf)
                if self.slide == 0:
                    self.page = self.source
                    self.page_size = Size(self.page.get_width(), self.page.get_height())
                else:
                    self.page = None
                    self.page_size = None
            elif self.filetype is ImageType.PDF:
                assert isinstance(self.source, Poppler.Document)
                if 0 <= self.slide < self.source.get_n_pages():
                    self.page = self.source.get_page(self.slide)
                else:
                    self.page = None
                if self.page is not None:
                    self.page_size = Size(self.page.get_size())
                else:
                    self.page_size = None
            else:
                self.page = None
            print(f"\tPresentation: page size: {self.page_size}")

        if self.pan_zoom_changed or needs_render:
            # Calculate the updated slide transformation
            needs_render = True

            # Fallback page size in case the slide did not load
            if self.page_size is None:
                self.page_size = Size(self.size)

            # The size of the portion of the slide that will be shown
            # zoom is a value in the interval (0, 1]
            size = Size(
                self.page_size.width * self.zoom.width,
                self.page_size.height * self.zoom.height,
            )
            # Determine the scale to make the visible portion of the slide fit the viewport
            scale = min(self.size.width / size.width, self.size.height / size.height)
            scaled_size = size * scale

            # Area above/below or left/right of visible portion that's empty in the viewport
            padding = Size(
                (self.size.width - scaled_size.width) / 2.0,
                (self.size.height - scaled_size.height) / 2.0,
            )

            # Calculate scale for whiteboard drawing relative to page size
            if self.tldraw_whiteboard:
                shapes_scale = max(
                    self.page_size.height / TLDRAW_DRAWING_SIZE.height,
                    self.page_size.width / TLDRAW_DRAWING_SIZE.width,
                )
            else:
                shapes_scale = max(
                    self.page_size.width / DRAWING_SIZE,
                    self.page_size.height / DRAWING_SIZE,
                )
            shapes_size = self.page_size / shapes_scale

            # Determine pan position (where the top left of the viewport is on the slide)
            if self.tldraw_whiteboard:
                pos = Position(-self.pan.x * shapes_scale, -self.pan.y * shapes_scale)
            else:
                pos = Position(
                    self.page_size.width * -self.pan.x,
                    self.page_size.height * -self.pan.y,
                )

            self.trans = Transform(padding, scale, size, pos, shapes_scale, shapes_size)
            self.print_transform()

        if needs_render:
            # Render the transformed slide to a pattern
            ctx = self.ctx
            ctx.push_group()

            if self.page:
                if self.filetype is ImageType.IMAGE:
                    assert isinstance(self.page, GdkPixbuf.Pixbuf)
                    apply_slide_transform(ctx, self.trans)
                    # Render on an opaque white background (transparent PNGs...)
                    ctx.set_source_rgb(1, 1, 1)
                    ctx.paint()
                    Gdk.cairo_set_source_pixbuf(ctx, self.page, 0, 0)
                    ctx.paint()
                elif self.filetype is ImageType.PDF:
                    assert isinstance(self.page, Poppler.Page)
                    assert self.page_size is not None
                    # This bit of nastiness is to work around Poppler bugs,
                    # which would otherwise contaminate the main cairo ctx
                    # with an error status, making it unusable.
                    try:
                        # Render the entire pdf page to a new image surface
                        # without clipping, to work around poppler bugs
                        pdfSurface = cairo.ImageSurface(
                            cairo.FORMAT_RGB24,
                            int(ceil(self.page_size.width * self.trans.scale)),
                            int(ceil(self.page_size.height * self.trans.scale)),
                        )
                        pdfCtx = cairo.Context(pdfSurface)
                        # on an opaque white background
                        pdfCtx.set_source_rgb(1, 1, 1)
                        pdfCtx.paint()
                        pdfCtx.scale(self.trans.scale, self.trans.scale)
                        self.page.render(pdfCtx)

                        pdfPattern = cairo.SurfacePattern(pdfSurface)

                        # Now render that image surface as a pattern onto
                        # the main context
                        # It is already rendered at 1:1 pixel ratio, so
                        # only translation and clipping should be used.
                        # Since it's an img src, it should be pixel aligned.
                        # padding
                        ctx.translate(
                            floor(self.trans.padding.width),
                            floor(self.trans.padding.height),
                        )
                        # clipping
                        ctx.rectangle(
                            0,
                            0,
                            ceil(self.trans.size.width * self.trans.scale),
                            ceil(self.trans.size.height * self.trans.scale),
                        )
                        ctx.clip()
                        # panning
                        ctx.translate(
                            ceil(-self.trans.pos.x * self.trans.scale),
                            ceil(-self.trans.pos.y * self.trans.scale),
                        )
                        ctx.set_source(pdfPattern)
                        ctx.paint()
                    except (SystemError, MemoryError) as e:
                        print(f"Poppler rendering failed: {e}")

            self.pattern = ctx.pop_group()

        self.presentation_changed = False
        self.slide_changed = False
        self.pan_zoom_changed = False
        return needs_render

    def render(self) -> None:
        """Composite the last-updated presentation image"""
        if self.pattern is not None:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
        else:
            print("No pattern to render!")
