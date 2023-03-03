# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, Generic, Optional, TypeVar

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Pango, PangoCairo

from bbb_presentation_video.events import (
    ClearEvent,
    PencilCommand,
    PresentationEvent,
    ShapeEvent,
    ShapeStatus,
    SlideEvent,
    UndoEvent,
)
from bbb_presentation_video.events.helpers import Color, Position
from bbb_presentation_video.renderer.presentation import (
    Transform,
    apply_shapes_transform,
)

BEZIER_CIRCLE_MAGIC = 0.551915024494

FONT_FAMILY = "Arial"

POLL_BAR_COLOR = Color.from_int(0x333333)
POLL_LINE_WIDTH = 2.0
POLL_FONT_SIZE = 22
POLL_BG = Color.from_int(0xFFFFFF)
POLL_FG = Color.from_int(0x000000)
POLL_VPADDING = 20.0
POLL_HPADDING = 10.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


class ShapesRenderer(Generic[CairoSomeSurface]):
    ctx: cairo.Context[CairoSomeSurface]

    presentation: Optional[str]
    presentation_slide: Dict[str, int]
    slide: int
    shapes: Dict[str, Dict[int, Deque[ShapeEvent]]]

    transform: Transform

    pattern: Optional[cairo.Pattern]

    shapes_changed: bool

    def __init__(self, ctx: cairo.Context[CairoSomeSurface], transform: Transform):
        self.ctx = ctx

        self.presentation = None
        self.presentation_slide = {}
        self.slide = 0
        self.shapes = {}

        self.transform = transform

        self.pattern = None

        self.shapes_changed = False

    def update_presentation(self, event: PresentationEvent) -> None:
        if self.presentation == event["presentation"]:
            print("\tShapes: presentation did not change")
            return
        self.presentation = event["presentation"]
        self.shapes_changed = True
        # Restore the last viewed page from this presentation
        self.slide = self.presentation_slide.get(self.presentation, 0)
        print(f"\tShapes: presentation: {self.presentation}")
        print(f"\tShapes: slide: {self.slide}")

    def update_slide(self, event: SlideEvent) -> None:
        if self.slide == event["slide"]:
            print("\tShapes: slide did not change")
            return
        self.slide = event["slide"]
        if self.presentation is not None:
            self.presentation_slide[self.presentation] = self.slide
        self.shapes_changed = True
        print(f"\tShapes: slide: {self.slide}")

    def ensure_shapes_structure(self, presentation: str, slide: int) -> None:
        if not presentation in self.shapes:
            self.shapes[presentation] = {}
        if not slide in self.shapes[presentation]:
            self.shapes[presentation][slide] = deque()

    def update_shape(self, event: ShapeEvent) -> None:
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)

        if presentation is None or slide is None:
            # Can't render a shape if there's nothing to render it on
            return

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
                new_points = list(prev_shape["points"])
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

    def update_undo(self, event: UndoEvent) -> None:
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)

        if presentation is None or slide is None:
            # Can't render a shape if there's nothing to render it on
            return

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

    def update_clear(self, event: ClearEvent) -> None:
        presentation = event.get("presentation", self.presentation)
        slide = event.get("slide", self.slide)

        if presentation is None or slide is None:
            # Can't render a shape if there's nothing to render it on
            return

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

    def shape_thickness(self, shape: ShapeEvent) -> float:
        thickness_ratio = shape.get("thickness_ratio")
        if thickness_ratio is not None:
            return thickness_ratio * self.transform.shapes_size.width

        thickness = shape["thickness"]
        assert thickness is not None

        return thickness

    def draw_pencil(self, shape: ShapeEvent) -> None:
        ctx = self.ctx
        ctx.set_source_rgb(*shape["color"])
        ctx.set_line_width(self.shape_thickness(shape))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        size = self.transform.shapes_size

        # The shape has commands, allowing curved lines
        if (
            "commands" in shape
            and shape["commands"] is not None
            and len(shape["points"]) > 1
        ):
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

    def draw_rectangle(self, shape: ShapeEvent) -> None:
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

    def draw_ellipse(self, shape: ShapeEvent) -> None:
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

    def draw_triangle(self, shape: ShapeEvent) -> None:
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

    def draw_line(self, shape: ShapeEvent) -> None:
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

    def draw_text(self, shape: ShapeEvent) -> None:
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

    def draw_poll_result(self, shape: ShapeEvent) -> None:
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

    def finalize_frame(self, transform: Transform) -> bool:
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

    def render(self) -> None:
        if self.pattern is not None:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
