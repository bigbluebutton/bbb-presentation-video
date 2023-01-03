from fractions import Fraction
from .events import Position, Size, Color, ShapeStatus, PencilCommand
from collections import deque
from math import pi, sqrt, ceil, floor
from subprocess import Popen, PIPE, CalledProcessError
from os.path import abspath, exists
from enum import Enum
import attr
from urllib.parse import urlunsplit
from urllib.parse import quote as urlquote
import cairo
import sys
from pkg_resources import resource_filename
import queue
import threading
import functools

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

gi.require_version("Poppler", "0.18")
from gi.repository import Poppler

gi.require_version("Pango", "1.0")
from gi.repository import Pango

gi.require_version("PangoCairo", "1.0")
from gi.repository import PangoCairo

# The size of the scaled coordinate system for drawing on slides
DRAWING_SIZE = 1200
DRAWING_BG = Color.from_int(0xE2E8ED)


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

LOGO_FILE = resource_filename(__name__, "bbb_logo.pdf")
LOGO_TYPE = ImageType.PDF

BEZIER_CIRCLE_MAGIC = 0.551915024494

CURSOR_OPACITY = 0.6
CURSOR_PRESENTER = Color.from_int(0xFF0000, CURSOR_OPACITY)
CURSOR_OTHER = Color.from_int(0x2A992A, CURSOR_OPACITY)
CURSOR_RADIUS = 0.005  # 6px on 960x720

FONT_FAMILY = "Arial"

POLL_BAR_COLOR = Color.from_int(0x333333)
POLL_LINE_WIDTH = 2.0
POLL_FONT_SIZE = 22
POLL_BG = Color.from_int(0xFFFFFF)
POLL_FG = Color.from_int(0x000000)
POLL_VPADDING = 20.0
POLL_HPADDING = 10.0


@attr.s
class Transform(object):
    padding = attr.ib()
    scale = attr.ib()
    size = attr.ib()
    pos = attr.ib()
    shapes_scale = attr.ib()
    shapes_size = attr.ib()


def apply_legacy_cursor_transform(ctx, t):
    ctx.translate(t.padding.width, t.padding.height)
    ctx.save()
    ctx.scale(t.scale, t.scale)
    ctx.rectangle(0, 0, t.size.width, t.size.height)
    ctx.restore()
    ctx.clip()


def apply_slide_transform(ctx, t):
    ctx.translate(t.padding.width, t.padding.height)
    ctx.scale(t.scale, t.scale)
    ctx.rectangle(0, 0, t.size.width, t.size.height)
    ctx.clip()
    ctx.translate(-t.pos.x, -t.pos.y)


def apply_shapes_transform(ctx, t):
    apply_slide_transform(ctx, t)
    ctx.scale(t.shapes_scale, t.shapes_scale)
    return t.shapes_size


class PresentationRenderer:
    def __init__(self, ctx, directory, size, hide_logo):
        self.ctx = ctx
        self.directory = directory
        self.size = Size(float(size.width), float(size.height))
        self.hide_logo = hide_logo

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
            Size(0.0, 0.0),
            1.0,
            self.size,
            Position(-0.0, -0.0),
            1.0,
            Size(DRAWING_SIZE, DRAWING_SIZE),
        )

    @property
    def transform(self):
        return self.trans

    def print_transform(self):
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

    def update_presentation(self, event):
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

    def update_slide(self, event):
        if self.slide == event["slide"]:
            print("\tPresentation: slide did not change")
            return
        self.slide = event["slide"]
        self.presentation_slide[self.presentation] = self.slide
        self.slide_changed = True
        print(f"\tPresentation: slide: {self.slide}")

    def update_pan_zoom(self, event):
        if self.pan == event["pan"] and self.zoom == event["zoom"]:
            print("\tPresentation: pan/zoom did not change")
            return
        self.pan = event["pan"]
        self.zoom = event["zoom"]
        self.pan_zoom_changed = True
        print(f"\tPresentation: pan: {self.pan} zoom: {self.zoom}")

    def finalize_frame(self):
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
                for extension in TYPE_MAP:
                    filename = f"{self.directory}/presentation/{self.presentation}/{self.presentation}.{extension}"
                    if exists(filename):
                        self.filename = filename
                        self.filetype = TYPE_MAP[extension]
                        break
            print(f"\tPresentation: filename: {self.filename}, type: {self.filetype}")

            # Load the source for the new presentation
            if self.filetype is ImageType.IMAGE:
                try:
                    self.source = GdkPixbuf.Pixbuf.new_from_file(self.filename)
                except GLib.GError as error:
                    print(f"Failed to read image: {error}")
                    self.presentation = None
                    self.filetype = ImageType.MISSING
            elif self.filetype is ImageType.PDF:
                try:
                    self.filename = urlunsplit(
                        ("file", "", urlquote(abspath(self.filename)), "", "")
                    )
                    self.source = Poppler.Document.new_from_file(self.filename, None)
                except GLib.GError as error:
                    print(f"Failed to read pdf: {error}")
                    self.presentation = None
                    self.filetype = ImageType.MISSING

        if self.slide_changed or needs_render:
            needs_render = True
            # Load the correct page
            if self.filetype is ImageType.IMAGE:
                if self.slide == 0:
                    self.page = self.source
                    self.page_size = Size(
                        float(self.page.get_width()), float(self.page.get_height())
                    )
                else:
                    self.page = None
            elif self.filetype is ImageType.PDF:
                if self.slide >= 0 and self.slide < self.source.get_n_pages():
                    self.page = self.source.get_page(self.slide)
                else:
                    self.page = None
                if self.page is not None:
                    (page_width, page_height) = self.page.get_size()
                    self.page_size = Size(float(page_width), float(page_height))
            else:
                self.page = None
            if self.page is None:
                self.page_size = Size(float(self.size.width), float(self.size.height))
            print(f"\tPresentation: page size: {self.page_size}")

        if self.pan_zoom_changed or needs_render:
            needs_render = True
            # Calculate the updated slide transformation
            pos = Position(
                self.page_size.width * -self.pan.x, self.page_size.height * -self.pan.y
            )
            size = Size(
                self.page_size.width * self.zoom.width,
                self.page_size.height * self.zoom.height,
            )

            print(f"\tPresentation: screen size: {self.size}")
            if (size.width / size.height) > (self.size.width / self.size.height):
                print("\tPresentation: scaling based on width")
                scale = self.size.width / size.width
            else:
                print("\tPresentation: scaling based on height")
                scale = self.size.height / size.height

            scaled_size = Size(scale * size.width, scale * size.height)
            padding = Size(
                (self.size.width - scaled_size.width) / 2.0,
                (self.size.height - scaled_size.height) / 2.0,
            )

            # Calculate the updated drawing transformation
            if self.page_size.height > self.page_size.width:
                shapes_scale = self.page_size.height / DRAWING_SIZE
                shapes_size = Size(
                    DRAWING_SIZE / self.page_size.height * self.page_size.width,
                    DRAWING_SIZE,
                )
            else:
                shapes_scale = self.page_size.width / DRAWING_SIZE
                shapes_size = Size(
                    DRAWING_SIZE,
                    DRAWING_SIZE / self.page_size.width * self.page_size.height,
                )

            self.trans = Transform(padding, scale, size, pos, shapes_scale, shapes_size)
            self.print_transform()

        if needs_render:
            # Render the transformed slide to a pattern
            ctx = self.ctx
            ctx.push_group()

            if self.page:
                if self.filetype is ImageType.IMAGE:
                    apply_slide_transform(ctx, self.trans)
                    # Render on an opaque white background (transparent PNGs...)
                    ctx.set_source_rgb(1, 1, 1)
                    ctx.paint()
                    Gdk.cairo_set_source_pixbuf(ctx, self.page, 0, 0)
                    ctx.paint()
                elif self.filetype is ImageType.PDF:
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

    def render(self):
        """Composite the last-updated presentation image"""
        if self.pattern:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
        else:
            print("No pattern to render!")


@attr.s
class Cursor(object):
    label = attr.ib()
    position = attr.ib(default=None)


class CursorRenderer:
    def __init__(self, ctx, size):
        self.ctx = ctx
        self.cursors = {}
        self.legacy_cursor = Cursor(label=None)
        self.cursors_changed = False
        self.presenter = None
        self.transform = None

        # Multi-pod cursors need to track presentation/slide
        self.presentation = None
        self.presentation_slide = {}
        self.slide = 0

        self.pattern = None
        self.radius = CURSOR_RADIUS * sqrt(
            size.width * size.width + size.height * size.height
        )

    def update_presentation(self, event):
        if self.presentation == event["presentation"]:
            print("\tCursor: presentation did not change")
            return
        self.presentation = event["presentation"]

        # Restore the last viewed page from this presentation
        self.slide = self.presentation_slide.get(self.presentation, 0)

        # All cursors are hidden on presentation/slide switch
        for user_id, cursor in self.cursors.items():
            cursor.position = None
        self.cursors_changed = True
        print("\tCursor: all cursors moved offscreen")

        print(f"\tCursor: presentation: {self.presentation}")
        print(f"\tCursor: slide: {self.slide}")

    def update_slide(self, event):
        if self.slide == event["slide"]:
            print("\tCursor: slide did not change")
            return
        self.slide = event["slide"]
        self.presentation_slide[self.presentation] = self.slide

        # All cursors are hidden on presentation/slide switch
        for user_id, cursor in self.cursors.items():
            cursor.position = None
        print("\tCursor: all cursors moved offscreen")
        self.cursors_changed = True

        print(f"\tCursor: slide: {self.slide}")

    def update_presenter(self, event):
        if self.presenter == event["user_id"]:
            print("\tCursor: presenter did not change")
            return
        self.presenter = event["user_id"]
        print(f"\tCursor: presenter is now {self.presenter}")
        self.cursors_changed = True

    def update_join(self, event):
        self.cursors[event["user_id"]] = Cursor(label=event["user_name"])

    def update_left(self, event):
        cursor = self.cursors.pop(event["user_id"], None)
        if cursor is not None and cursor.position is not None:
            print(f"\tCursors: removing cursor for {event['user_id']}")
            self.cursors_changed = True

    def update_cursor(self, event):
        cursor = self.legacy_cursor
        if cursor.position == event["cursor"]:
            print("\tLegacy cursor: position did not change")
            return
        cursor.position = event["cursor"]
        if cursor.position is not None:
            print(f"\tLegacy cursor: position: {cursor.position * 100}")
        else:
            print("\tLegacy cursor: offscreen")
        self.cursors_changed = True

    def update_cursor_v2(self, event):
        # Ignore cursor updates from other pods by checking against the
        # current presentation and slide.
        presentation = event.get("presentation")
        slide = event.get("slide")
        if presentation is not None or slide is not None:
            if presentation != self.presentation or slide != self.slide:
                print("\tCursor: not on current presentation/slide, skipping")
                return

        user_id = event["user_id"]
        cursor = self.cursors.get(user_id)
        if cursor is None:
            print(f"\tCursor: user_id {user_id}: user not present, ignoring")
            return

        if cursor.position == event["cursor"]:
            print(f"\tCursor: user_id {user_id}: position did not change")
            return

        cursor.position = event["cursor"]
        if cursor.position is not None:
            print(f"\tCursor: user_id {user_id}: position: {cursor.position * 100}")
        else:
            print(f"\tCursor: user_id {user_id}: offscreen")
        self.cursors_changed = True

    # To make the recording look prettier, use some shape updates to also
    # update the cursor position.
    def update_shape(self, event):
        # Only do this if we know who is drawing the shape,
        user_id = event.get("user_id")
        if user_id is None:
            return

        # Check that it's on the current presentation/slide
        if event["presentation"] != self.presentation or event["slide"] != self.slide:
            return

        # And they already have a cursor visible
        cursor = self.cursors.get(user_id)
        if cursor is None or cursor.position is None:
            return

        # Whitelist of shapes which work well for cursor updates
        # Ignore the 'DRAW_END' messages, since they can happen late
        if (
            event["shape_type"]
            in ["pencil", "rectangle", "ellipse", "triangle", "line"]
            and event["shape_status"] != ShapeStatus.DRAW_END
        ):
            cursor.position = event["points"][-1]
            print(
                f"\tCursor: user_id {user_id}: update from shape, position: {cursor.position * 100}"
            )
            self.cursors_changed = True

    def finalize_frame(self, transform):
        if (not self.cursors_changed) and self.transform == transform:
            return False

        self.transform = transform

        ctx = self.ctx
        ctx.push_group()

        if self.legacy_cursor.position is not None:
            cursor = self.legacy_cursor

            ctx.save()
            apply_legacy_cursor_transform(ctx, transform)
            x1, y1, x2, y2 = ctx.clip_extents()

            screen_pos = Position(
                (x2 - x1) * cursor.position.x, (y2 - y1) * cursor.position.y
            )
            print(f"\tLegacy cursor: screen position: {screen_pos}")

            ctx.translate(*screen_pos)
            ctx.arc(0, 0, self.radius, 0, 2 * pi)
            ctx.set_source_rgba(*CURSOR_PRESENTER)
            ctx.fill()
            ctx.restore()

        for user_id, cursor in self.cursors.items():
            if cursor.position is None:
                continue

            ctx.save()
            apply_shapes_transform(ctx, transform)
            pos = Position(
                cursor.position.x * transform.shapes_size.width,
                cursor.position.y * transform.shapes_size.height,
            )
            print(f"\tCursor: user_id: {user_id}: slide position: {pos}")

            ctx.translate(*pos)

            ctx.arc(
                0, 0, self.radius / transform.shapes_scale / transform.scale, 0, 2 * pi
            )
            if user_id == self.presenter:
                ctx.set_source_rgba(*CURSOR_PRESENTER)
                ctx.set_operator(cairo.OPERATOR_OVER)
            else:
                ctx.set_source_rgba(*CURSOR_OTHER)
                ctx.set_operator(cairo.OPERATOR_DEST_OVER)
            ctx.fill()
            ctx.restore()

        self.pattern = ctx.pop_group()

        self.cursors_changed = False
        return True

    def render(self):
        if self.pattern:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()


class ShapesRenderer:
    def __init__(self, ctx):
        self.ctx = ctx

        self.presentation = None
        self.presentation_slide = {}
        self.slide = 0
        self.shapes = {}

        self.transform = None

        self.pattern = None

        self.shapes_changed = False

    def update_presentation(self, event):
        if self.presentation == event["presentation"]:
            print("\tShapes: presentation did not change")
            return
        self.presentation = event["presentation"]
        self.shapes_changed = True
        # Restore the last viewed page from this presentation
        self.slide = self.presentation_slide.get(self.presentation, 0)
        print(f"\tShapes: presentation: {self.presentation}")
        print(f"\tShapes: slide: {self.slide}")

    def update_slide(self, event):
        if self.slide == event["slide"]:
            print("\tShapes: slide did not change")
            return
        self.slide = event["slide"]
        self.presentation_slide[self.presentation] = self.slide
        self.shapes_changed = True
        print(f"\tShapes: slide: {self.slide}")

    def ensure_shapes_structure(self, presentation, slide):
        if not presentation in self.shapes:
            self.shapes[presentation] = {}
        if not slide in self.shapes[presentation]:
            self.shapes[presentation][slide] = deque()

    def update_shape(self, event):
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)
        self.ensure_shapes_structure(presentation, slide)

        if (
            "slide" not in event
            and event["shape_type"] == "text"
            and event["shape_status"] == ShapeStatus.DRAW_END
        ):
            print(
                f"\tShapes: ignoring textPublished event without page info for {event['shape_id']}"
            )
            return

        # Locate the previous version of the current shape
        prev_index = None
        if event["shape_id"] is not None:
            # Look up the previous version of the shape by id, if available
            prev_index = next(
                (
                    i
                    for i, x in enumerate(self.shapes[presentation][slide])
                    if x["shape_id"] == event["shape_id"]
                ),
                None,
            )
            if prev_index is not None:
                print(
                    f"\tShapes: replacing shape with same id {event['shape_id']} at index {prev_index}"
                )
        else:
            # Horrible hack to support old recordings
            if len(self.shapes[presentation][slide]) > 0:
                prev_shape = self.shapes[presentation][slide][-1]
                if (
                    prev_shape["points"][0] == event["points"][0]
                    and prev_shape["shape_type"] == event["shape_type"]
                ):
                    prev_index = -1
                    print(
                        f"\tShapes: replacing shape with same initial point {event['points'][0]} at index {prev_index}"
                    )

        if prev_index is not None:
            # Special case: DRAW_UPDATE on a pencil doesn't include the full
            # point list. Need to prepend the points from the previous event
            if (
                event["shape_type"] == "pencil"
                and event.get("shape_status") == ShapeStatus.DRAW_UPDATE
            ):
                prev_shape = self.shapes[presentation][slide][prev_index]
                new_points = deque(prev_shape["points"])
                new_points.extend(event["points"])
                event["points"] = new_points

            self.shapes[presentation][slide][prev_index] = event
        else:
            self.shapes[presentation][slide].append(event)
        print(
            f"\tShapes: add {event['shape_type']} id: {event['shape_id']} "
            f"presentation: {presentation} slide: {slide} points: {event['points']}"
        )
        self.shapes_changed = True

    def update_undo(self, event):
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)
        self.ensure_shapes_structure(presentation, slide)

        # If the undo event has a shape id, use that to lookup the shape
        shape_id = event.get("shape_id")
        if shape_id is not None:
            self.shapes[presentation][slide] = deque(
                [
                    x
                    for x in self.shapes[presentation][slide]
                    if x["shape_id"] != shape_id
                ]
            )
            self.shapes_changed = True
            print(f"\tShapes: undo removed id: {shape_id}")

        # Undo without a shape id just removes the most recently added shape
        else:
            if len(self.shapes[presentation][slide]) > 0:
                shape = self.shapes[presentation][slide].pop()
                self.shapes_changed = True
                print(
                    f"\tShapes: undo removed last added shape, id: {shape['shape_id']}"
                )

    def update_clear(self, event):
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)
        self.ensure_shapes_structure(presentation, slide)

        # When the full_clear status is set, or if the recording does not have
        # that attribute, simply remove all shapes
        if event.get("full_clear", True):
            self.shapes[presentation][slide] = deque()
            self.shapes_changed = True
            print("\tShapes: cleared all shapes")

        # Otherwise we have to remove only shapes for a specific user
        else:
            self.shapes[presentation][slide] = deque(
                [
                    x
                    for x in self.shapes[presentation][slide]
                    if x["user_id"] != event["user_id"]
                ]
            )
            self.shapes_changed = True
            print(f"\tShapes: cleared shapes for user {event['user_id']}")

    def shape_thickness(self, shape):
        thickness = shape.get("thickness_ratio")
        if thickness is not None:
            thickness = thickness * self.transform.shapes_size.width
        else:
            thickness = shape["thickness"]
        return thickness

    def draw_pencil(self, shape):
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        size = self.transform.shapes_size

        # The shape has commands, allowing curved lines
        if "commands" in shape and len(shape["points"]) > 1:
            try:
                commands_iter = iter(shape["commands"])
                points_iter = iter(shape["points"])
                prev_point = shape["points"][0]
                while True:
                    command = next(commands_iter)
                    if command is PencilCommand.MOVE_TO:
                        point = next(points_iter)
                        ctx.move_to(point.x * size.width, point.y * size.height)
                    elif command is PencilCommand.LINE_TO:
                        point = next(points_iter)
                        ctx.line_to(point.x * size.width, point.y * size.height)
                    elif command is PencilCommand.Q_CURVE_TO:
                        qc = next(points_iter)
                        point = next(points_iter)
                        # Cairo only has cubic curves, so we have to convert
                        cc1 = Position(
                            prev_point.x + (qc.x - prev_point.x) * 2 / 3,
                            prev_point.y + (qc.y - prev_point.y) * 2 / 3,
                        )
                        cc2 = Position(
                            point.x + (qc.x - point.x) * 2 / 3,
                            point.y + (qc.y - point.y) * 2 / 3,
                        )
                        ctx.curve_to(
                            cc1.x * size.width,
                            cc1.y * size.height,
                            cc2.x * size.width,
                            cc2.y * size.height,
                            point.x * size.width,
                            point.y * size.height,
                        )
                    elif command is PencilCommand.C_CURVE_TO:
                        c1 = next(points_iter)
                        c2 = next(points_iter)
                        point = next(points_iter)
                        ctx.curve_to(
                            c1.x * size.width,
                            c1.y * size.height,
                            c2.x * size.width,
                            c2.y * size.height,
                            point.x * size.width,
                            point.y * size.height,
                        )
                    else:
                        print(f"\tShapes: Unknown command in pencil: {command}")
                    prev_point = point
            except StopIteration:
                pass
            ctx.stroke()

        # Simple line
        else:
            print(f"Points: {shape['points']!r}")
            point = shape["points"][0]
            ctx.move_to(point.x * size.width, point.y * size.height)
            try:
                points_iter = iter(shape["points"])
                while True:
                    point = next(points_iter)
                    ctx.line_to(point.x * size.width, point.y * size.height)
            except StopIteration:
                pass
            ctx.stroke()

    def draw_rectangle(self, shape):
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))
        if shape.get("rounded", True):
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        else:
            ctx.set_line_join(cairo.LINE_JOIN_MITER)

        points_iter = iter(shape["points"])
        a = next(points_iter)
        b = next(points_iter)
        size = self.transform.shapes_size

        x1, y1 = a.x * size.width, a.y * size.height
        x2, y2 = b.x * size.width, b.y * size.height

        width = abs(x2 - x1)
        height = abs(y2 - y1)

        # Convert to a square, keeping aligned with the start point
        if shape["square"]:
            # This duplicates a bug in BigBlueButton client
            if x2 > x1:
                y2 = y1 + width
            else:
                y2 = y1 - width

        # The cairo rectangle behaves strangely when backwards, so just
        # make a path
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y1)
        ctx.line_to(x2, y2)
        ctx.line_to(x1, y2)
        ctx.close_path()
        ctx.stroke()

    def draw_ellipse(self, shape):
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))

        points_iter = iter(shape["points"])
        a = next(points_iter)
        b = next(points_iter)
        size = self.transform.shapes_size

        x1, y1 = a.x * size.width, a.y * size.height
        x2, y2 = b.x * size.width, b.y * size.height

        width_r = abs(x2 - x1) / 2
        height_r = abs(y2 - y1) / 2

        # Convert to a circle, keeping aligned with the start point
        if shape["circle"]:
            height_r = width_r
            # This duplicates a bug in BigBlueButton client
            if x2 > x1:
                y2 = y1 + width_r + width_r
            else:
                y2 = y1 - width_r - width_r

        # Draw a bezier approximation to the ellipse. Cairo's arc function
        # doesn't deal well with degenerate (0-height/width) ellipses because
        # of the scaling required.
        ctx.translate((x1 + x2) / 2, (y1 + y2) / 2)
        ctx.move_to(-width_r, 0)
        ctx.curve_to(
            -width_r,
            -height_r * BEZIER_CIRCLE_MAGIC,
            -width_r * BEZIER_CIRCLE_MAGIC,
            -height_r,
            0,
            -height_r,
        )
        ctx.curve_to(
            width_r * BEZIER_CIRCLE_MAGIC,
            -height_r,
            width_r,
            -height_r * BEZIER_CIRCLE_MAGIC,
            width_r,
            0,
        )
        ctx.curve_to(
            width_r,
            height_r * BEZIER_CIRCLE_MAGIC,
            width_r * BEZIER_CIRCLE_MAGIC,
            height_r,
            0,
            height_r,
        )
        ctx.curve_to(
            -width_r * BEZIER_CIRCLE_MAGIC,
            height_r,
            -width_r,
            height_r * BEZIER_CIRCLE_MAGIC,
            -width_r,
            0,
        )
        ctx.close_path()
        ctx.stroke()

    def draw_triangle(self, shape):
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))
        if shape.get("rounded", True):
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        else:
            ctx.set_line_join(cairo.LINE_JOIN_MITER)
            ctx.set_miter_limit(8)

        points_iter = iter(shape["points"])
        a = next(points_iter)
        b = next(points_iter)
        size = self.transform.shapes_size

        x1, y1 = a.x * size.width, a.y * size.height
        x2, y2 = b.x * size.width, b.y * size.height

        ctx.move_to(x1, y2)
        ctx.line_to((x1 + x2) / 2, y1)
        ctx.line_to(x2, y2)
        ctx.close_path()
        ctx.stroke()

    def draw_line(self, shape):
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))
        if shape.get("rounded", True):
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        else:
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)

        points_iter = iter(shape["points"])
        x1, y1 = next(points_iter)
        x2, y2 = next(points_iter)
        size = self.transform.shapes_size

        ctx.move_to(x1 * size.width, y1 * size.height)
        ctx.line_to(x2 * size.width, y2 * size.height)
        ctx.stroke()

    def draw_text(self, shape):
        point_iter = iter(shape["points"])
        x, y = next(point_iter)

        size = self.transform.shapes_size
        rect_width = shape["width"] * size.width
        rect_height = shape["height"] * size.height

        font = Pango.FontDescription()
        font.set_family(FONT_FAMILY)
        font_size = shape["calced_font_size"] * size.height
        font.set_absolute_size(int(font_size * Pango.SCALE))

        ctx = self.ctx
        ctx.set_source_rgb(*shape["font_color"])
        ctx.translate(x * size.width, y * size.height)

        pctx = PangoCairo.create_context(ctx)
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_GRAY)
        fo.set_hint_metrics(cairo.HINT_METRICS_ON)
        fo.set_hint_style(cairo.HINT_STYLE_NONE)
        PangoCairo.context_set_font_options(pctx, fo)
        layout = Pango.Layout(pctx)
        layout.set_font_description(font)
        layout.set_width(int(rect_width * Pango.SCALE))
        # The font size stuff is so iffy that I don't want to clip, let it
        # overflow to arbitrary height.
        # layout.set_height(int(rect_height * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_text(shape["text"], -1)

        PangoCairo.show_layout(ctx, layout)

    def draw_poll_result(self, shape):
        if len(shape["result"]) == 0:
            return

        ctx = self.ctx

        point_iter = iter(shape["points"])
        x, y = next(point_iter)
        width, height = next(point_iter)

        size = self.transform.shapes_size
        x, y = x * size.width, y * size.height
        width, height = width * size.width, height * size.height

        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

        # Draw the background and poll outline
        half_lw = POLL_LINE_WIDTH / 2
        ctx.set_line_width(POLL_LINE_WIDTH)
        ctx.move_to(x + half_lw, y + half_lw)
        ctx.line_to(x + width - half_lw, y + half_lw)
        ctx.line_to(x + width - half_lw, y + height - half_lw)
        ctx.line_to(x + half_lw, y + height - half_lw)
        ctx.close_path()
        ctx.set_source_rgb(*POLL_BG)
        ctx.fill_preserve()
        ctx.set_source_rgb(*POLL_FG)
        ctx.stroke()

        font = Pango.FontDescription()
        font.set_family(FONT_FAMILY)
        font.set_absolute_size(int(POLL_FONT_SIZE * Pango.SCALE))

        # Use Pango to calculate the label width space needed
        pctx = PangoCairo.create_context(ctx)
        layout = Pango.Layout(pctx)
        layout.set_font_description(font)

        max_label_width = 0.0
        max_percent_width = 0.0
        for result in shape["result"]:
            layout.set_text(result["key"], -1)
            (label_width, _) = layout.get_pixel_size()
            if label_width > max_label_width:
                max_label_width = label_width
            if shape["num_responders"] > 0:
                result["percent"] = "{}%".format(
                    int(
                        float(result["num_votes"])
                        / float(shape["num_responders"])
                        * 100
                    )
                )
            else:
                result["percent"] = "0%"
            layout.set_text(result["percent"], -1)
            (percent_width, _) = layout.get_pixel_size()
            if percent_width > max_percent_width:
                max_percent_width = percent_width

        max_label_width = min(max_label_width, width * 0.3)
        max_percent_width = min(max_percent_width, width * 0.3)

        bar_height = (height - POLL_VPADDING) / len(shape["result"]) - POLL_VPADDING
        bar_width = width - 4 * POLL_HPADDING - max_label_width - max_percent_width
        bar_x = x + 2 * POLL_HPADDING + max_label_width

        # All sizes are calculated, so draw the poll
        for i, result in enumerate(shape["result"]):
            bar_y = y + (bar_height + POLL_VPADDING) * i + POLL_VPADDING
            if shape["num_responders"] > 0:
                result_ratio = float(result["num_votes"]) / float(
                    shape["num_responders"]
                )
            else:
                result_ratio = 0.0

            bar_x2 = bar_x + (bar_width * result_ratio)

            # Draw the bar
            ctx.set_line_width(POLL_LINE_WIDTH)
            ctx.move_to(bar_x + half_lw, bar_y + half_lw)
            ctx.line_to(max(bar_x + half_lw, bar_x2 - half_lw), bar_y + half_lw)
            ctx.line_to(
                max(bar_x + half_lw, bar_x2 - half_lw), bar_y + bar_height - half_lw
            )
            ctx.line_to(bar_x + half_lw, bar_y + bar_height - half_lw)
            ctx.close_path()
            ctx.set_source_rgb(*POLL_BAR_COLOR)
            ctx.fill_preserve()
            ctx.stroke()

            # Draw the label and percentage
            layout.set_ellipsize(Pango.EllipsizeMode.END)
            ctx.set_source_rgb(*POLL_FG)
            layout.set_width(int(max_label_width * Pango.SCALE))
            layout.set_text(result["key"], -1)
            label_width, label_height = layout.get_pixel_size()
            ctx.move_to(
                bar_x - POLL_HPADDING - label_width,
                bar_y + (bar_height - label_height) / 2,
            )
            PangoCairo.show_layout(ctx, layout)
            layout.set_width(int(max_percent_width * Pango.SCALE))
            layout.set_text(result["percent"], -1)
            percent_width, percent_height = layout.get_pixel_size()
            ctx.move_to(
                x + width - POLL_HPADDING - percent_width,
                bar_y + (bar_height - percent_height) / 2,
            )
            PangoCairo.show_layout(ctx, layout)

            # Draw the result count
            layout.set_ellipsize(Pango.EllipsizeMode.NONE)
            layout.set_width(-1)
            layout.set_text(str(result["num_votes"]), -1)
            votes_width, votes_height = layout.get_pixel_size()
            if votes_width < (bar_x2 - bar_x - 2 * POLL_HPADDING):
                # Votes fit in the bar
                ctx.move_to(
                    bar_x + (bar_x2 - bar_x - votes_width) / 2,
                    bar_y + (bar_height - votes_height) / 2,
                )
                ctx.set_source_rgb(*POLL_BG)
                PangoCairo.show_layout(ctx, layout)
            else:
                # Votes do not fit in the bar, so put them after
                ctx.move_to(
                    bar_x2 + POLL_HPADDING, bar_y + (bar_height - votes_height) / 2
                )
                ctx.set_source_rgb(*POLL_FG)
                PangoCairo.show_layout(ctx, layout)

    def finalize_frame(self, transform):
        try:
            if not self.shapes_changed and self.transform == transform:
                return False
            self.transform = transform

            if (
                self.presentation is None
                or not self.presentation in self.shapes
                or not self.slide in self.shapes[self.presentation]
            ):
                if self.pattern:
                    print("\tShapes: no shapes to render")
                    self.pattern = None
                    return True
                else:
                    return False

            print(
                f"\tShapes: rendering {len(self.shapes[self.presentation][self.slide])} shapes"
            )

            ctx = self.ctx
            ctx.push_group()
            apply_shapes_transform(ctx, self.transform)

            for shape in self.shapes[self.presentation][self.slide]:
                ctx.save()
                type = shape["shape_type"]
                if type == "pencil":
                    self.draw_pencil(shape)
                elif type == "rectangle":
                    self.draw_rectangle(shape)
                elif type == "ellipse":
                    self.draw_ellipse(shape)
                elif type == "triangle":
                    self.draw_triangle(shape)
                elif type == "line":
                    self.draw_line(shape)
                elif type == "text":
                    self.draw_text(shape)
                elif type == "poll_result":
                    self.draw_poll_result(shape)
                else:
                    print(f"\tShapes: don't know how to draw {type}")
                ctx.restore()

            self.pattern = ctx.pop_group()

            return True
        finally:
            self.shapes_changed = False

    def render(self):
        if self.pattern:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()


class Encoder:
    def __init__(self, output, width, height, framerate):
        self.output = output
        self.width = width
        self.height = height
        self.framerate = framerate

        self.queue = queue.Queue()
        self.ret_queue = queue.Queue()
        for x in range(0, 3):
            self.ret_queue.put(bytearray(width * height * 4))

        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()

    def put(self, data):
        buf = self.ret_queue.get()
        buf[:] = data
        self.queue.put(buf)

    def join(self):
        # This is a sentinal value to tell the writing thread to exit
        self.queue.put(None)
        self.thread.join()

    def run(self):
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
            "-c:v",
            "libx264",
            "-qp",
            "0",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-g",
            str(round(self.framerate) * 10),
            "-f",
            "matroska",
            self.output,
        ]

        ffmpeg = Popen(ffmpeg_cmdline, stdin=PIPE, stdout=PIPE, close_fds=True)
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
    def __init__(
        self,
        events,
        length,
        input,
        output,
        width,
        height,
        framerate,
        start_time,
        end_time,
        pod_id,
        hide_logo,
    ):
        # The events get modified, so make a copy of the queue
        self.events = deque(events)
        self.length = length
        self.input = input
        self.output = output
        self.size = Size(width, height)
        self.framerate = framerate
        self.pod_id = pod_id
        self.hide_logo = hide_logo

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
        self.surface = cairo.ImageSurface(
            cairo.FORMAT_RGB24, self.size.width, self.size.height
        )
        self.ctx = cairo.Context(self.surface)

        # Set up font rendering options
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.ANTIALIAS_GRAY)
        font_options.set_hint_style(cairo.HINT_STYLE_NONE)
        self.ctx.set_font_options(font_options)

    def update_record(self, event):
        if self.recording != event["status"]:
            self.recording = event["status"]
            print(f"\tRenderer: recording: {self.recording}")

    def render(self):

        cursor = CursorRenderer(self.ctx, self.size)
        presentation = PresentationRenderer(
            self.ctx, self.input, self.size, self.hide_logo
        )
        shapes = ShapesRenderer(self.ctx)

        encoder = Encoder(
            self.output, self.size.width, self.size.height, self.framerate
        )

        presentation_changed = True
        shapes_changed = False
        cursor_changed = False
        recording_changed = False
        while self.pts < self.length:

            event_ts = 0
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
                    if event["pod_id"] != self.pod_id:
                        print(f"\tskipping event for pod {event['pod_id']}")
                        continue

                if name == "cursor":
                    cursor.update_cursor(event)
                elif name == "cursor_v2":
                    cursor.update_cursor_v2(event)
                elif name == "pan_zoom":
                    presentation.update_pan_zoom(event)
                elif name == "presentation":
                    presentation.update_presentation(event)
                    shapes.update_presentation(event)
                    cursor.update_presentation(event)
                elif name == "slide":
                    presentation.update_slide(event)
                    shapes.update_slide(event)
                    cursor.update_slide(event)
                elif name == "shape":
                    shapes.update_shape(event)
                    cursor.update_shape(event)
                elif name == "undo":
                    shapes.update_undo(event)
                elif name == "clear":
                    shapes.update_clear(event)
                elif name == "record":
                    self.update_record(event)
                    recording_changed = True
                elif name == "presenter":
                    cursor.update_presenter(event)
                elif name == "join":
                    cursor.update_join(event)
                elif name == "left":
                    cursor.update_left(event)
                else:
                    print("\tdon't know how to handle this event")

            if self.recording and self.pts >= self.start_time:
                presentation_changed = presentation.finalize_frame()
                shapes_changed = shapes.finalize_frame(presentation.transform)
                cursor_changed = cursor.finalize_frame(presentation.transform)

                if presentation_changed or shapes_changed or cursor_changed:
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
