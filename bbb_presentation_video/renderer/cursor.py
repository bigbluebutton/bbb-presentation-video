# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from math import pi, sqrt
from typing import Dict, Generic, Optional, TypeVar

import attr
import cairo

from bbb_presentation_video.events import (
    CursorEvent,
    JoinEvent,
    LeftEvent,
    PresentationEvent,
    PresenterEvent,
    ShapeEvent,
    ShapeStatus,
    Size,
    SlideEvent,
    WhiteboardCursorEvent,
)
from bbb_presentation_video.events.helpers import Color, Position
from bbb_presentation_video.renderer.presentation import (
    Transform,
    apply_shapes_transform,
    apply_slide_transform,
)

CURSOR_OPACITY = 0.6
CURSOR_PRESENTER = Color.from_int(0xFF0000, CURSOR_OPACITY)
CURSOR_OTHER = Color.from_int(0x2A992A, CURSOR_OPACITY)
CURSOR_RADIUS = 0.005  # 6px on 960x720

CairoSomeSurface = TypeVar("CairoSomeSurface", bound="cairo.Surface")


def apply_legacy_cursor_transform(
    ctx: "cairo.Context[CairoSomeSurface]", t: Transform
) -> None:
    ctx.translate(t.padding.width, t.padding.height)
    ctx.save()
    ctx.scale(t.scale, t.scale)
    ctx.rectangle(0, 0, t.size.width, t.size.height)
    ctx.restore()
    ctx.clip()


@attr.s(order=False, slots=True, auto_attribs=True)
class Cursor:
    label: Optional[str]
    position: Optional[Position] = None


class CursorRenderer(Generic[CairoSomeSurface]):
    ctx: "cairo.Context[CairoSomeSurface]"
    cursors: Dict[str, Cursor]
    legacy_cursor: Cursor

    cursors_changed: bool
    presenter: Optional[str]
    transform: Optional[Transform]
    tldraw_whiteboard: bool

    presentation: Optional[str]
    presentation_slide: Dict[str, int]
    slide: int

    pattern: Optional[cairo.Pattern]
    radius: float

    def __init__(
        self,
        ctx: "cairo.Context[CairoSomeSurface]",
        size: Size,
        *,
        tldraw_whiteboard: bool,
    ):
        self.ctx = ctx
        self.cursors = {}
        self.legacy_cursor = Cursor(label=None)
        self.cursors_changed = False
        self.presenter = None
        self.transform = None
        self.tldraw_whiteboard = tldraw_whiteboard

        # Multi-pod cursors need to track presentation/slide
        self.presentation = None
        self.presentation_slide = {}
        self.slide = 0

        self.pattern = None
        self.radius = CURSOR_RADIUS * sqrt(
            size.width * size.width + size.height * size.height
        )

    def update_presentation(self, event: PresentationEvent) -> None:
        presentation = event["presentation"]
        if self.presentation == presentation:
            print("\tCursor: presentation did not change")
            return
        self.presentation = presentation

        # Restore the last viewed page from this presentation
        self.slide = self.presentation_slide.get(presentation, 0)

        # All cursors are hidden on presentation/slide switch
        for user_id, cursor in self.cursors.items():
            cursor.position = None
        self.cursors_changed = True
        print("\tCursor: all cursors moved offscreen")

        print(f"\tCursor: presentation: {self.presentation}")
        print(f"\tCursor: slide: {self.slide}")

    def update_slide(self, event: SlideEvent) -> None:
        if self.slide == event["slide"]:
            print("\tCursor: slide did not change")
            return
        self.slide = event["slide"]
        if self.presentation is not None:
            self.presentation_slide[self.presentation] = self.slide

        # All cursors are hidden on presentation/slide switch
        for user_id, cursor in self.cursors.items():
            cursor.position = None
        print("\tCursor: all cursors moved offscreen")
        self.cursors_changed = True

        print(f"\tCursor: slide: {self.slide}")

    def update_presenter(self, event: PresenterEvent) -> None:
        if self.presenter == event["user_id"]:
            print("\tCursor: presenter did not change")
            return
        self.presenter = event["user_id"]
        print(f"\tCursor: presenter is now {self.presenter}")
        self.cursors_changed = True

    def update_join(self, event: JoinEvent) -> None:
        self.cursors[event["user_id"]] = Cursor(label=event["user_name"])

    def update_left(self, event: LeftEvent) -> None:
        cursor = self.cursors.pop(event["user_id"], None)
        if cursor is not None and cursor.position is not None:
            print(f"\tCursors: removing cursor for {event['user_id']}")
            self.cursors_changed = True

    def update_cursor(self, event: CursorEvent) -> None:
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

    def update_cursor_v2(self, event: WhiteboardCursorEvent) -> None:
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
            if self.tldraw_whiteboard:
                print(f"\tCursor: user_id: {user_id}, position: {cursor.position}")
            else:
                print(f"\tCursor: user_id {user_id}: position: {cursor.position * 100}")
        else:
            print(f"\tCursor: user_id {user_id}: offscreen")
        self.cursors_changed = True

    # To make the recording look prettier, use some shape updates to also
    # update the cursor position.
    def update_shape(self, event: ShapeEvent) -> None:
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

    def finalize_frame(self, transform: Transform) -> bool:
        if (not self.cursors_changed) and self.transform == transform:
            return False

        self.transform = transform

        ctx = self.ctx
        ctx.push_group()

        cursor = self.legacy_cursor
        if cursor.position is not None:
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
            if self.tldraw_whiteboard:
                pos = cursor.position
            else:
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

    def render(self) -> None:
        if self.pattern:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
