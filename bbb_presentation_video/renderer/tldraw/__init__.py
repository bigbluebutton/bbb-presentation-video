# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Dict, Generic, Optional, TypeVar, cast

import cairo
from sortedcollections import ValueSortedDict

from bbb_presentation_video import events
from bbb_presentation_video.events import Event, tldraw
from bbb_presentation_video.renderer.presentation import (
    Transform,
    apply_shapes_transform,
)
from bbb_presentation_video.renderer.tldraw.fonts import add_fontconfig_app_font_dir
from bbb_presentation_video.renderer.tldraw.shape import (
    ArrowShape,
    DrawShape,
    EllipseShape,
    GroupShape,
    RectangleShape,
    Shape,
    StickyShape,
    TextShape,
    TriangleShape,
    parse_shape_from_data,
    shape_sort_key,
)
from bbb_presentation_video.renderer.tldraw.shape.arrow import finalize_arrow
from bbb_presentation_video.renderer.tldraw.shape.draw import finalize_draw
from bbb_presentation_video.renderer.tldraw.shape.ellipse import finalize_ellipse
from bbb_presentation_video.renderer.tldraw.shape.rectangle import finalize_rectangle
from bbb_presentation_video.renderer.tldraw.shape.sticky import finalize_sticky
from bbb_presentation_video.renderer.tldraw.shape.text import finalize_text
from bbb_presentation_video.renderer.tldraw.shape.triangle import finalize_triangle

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


class TldrawRenderer(Generic[CairoSomeSurface]):
    """Render tldraw whiteboard shapes"""

    ctx: cairo.Context[CairoSomeSurface]
    """The cairo rendering context for drawing the whiteboard."""

    presentation: Optional[str] = None
    """The current presentation."""

    slide: Optional[int] = None
    """The current slide."""

    presentation_slide: Dict[str, int]
    """The last shown slide on a given presentation."""

    shapes: Dict[str, Dict[int, ValueSortedDict[str, Shape]]]
    """The list of shapes, organized by presentation then slide."""

    shapes_changed: bool = False
    """Whether there have been changes to rendered shapes since the last frame."""

    transform: Transform
    """The current transform."""

    pattern: Optional[cairo.SurfacePattern] = None
    """Cached rendered whiteboard."""

    shape_patterns: Dict[str, cairo.SurfacePattern]
    """Cached rendered individual shapes for current presentation/slide."""

    def __init__(self, ctx: cairo.Context[CairoSomeSurface], transform: Transform):
        self.ctx = ctx
        self.presentation_slide = {}
        self.shapes = {}
        self.shape_patterns = {}
        self.transform = transform

        add_fontconfig_app_font_dir()

    def ensure_shape_structure(self, presentation: str, slide: int) -> None:
        """Create the nested dict entries for storing shapes per presentation and slide."""
        try:
            p = self.shapes[presentation]
        except KeyError:
            p = self.shapes[presentation] = {}
        try:
            p[slide]
        except KeyError:
            p[slide] = ValueSortedDict(shape_sort_key)

    def presentation_event(self, event: events.PresentationEvent) -> None:
        """Handler for PresentationEvent updates."""
        presentation = event["presentation"]
        if self.presentation == presentation:
            print("\tTldraw: presentation did not change")
            return

        # Only keep cached shape patterns for the current presentation/slide
        self.shape_patterns.clear()

        self.presentation = presentation
        self.slide = self.presentation_slide.get(presentation, 0)
        self.shapes_changed = True
        print(f"\tTldraw: presentation: {self.presentation}, slide: {self.slide}")

    def slide_event(self, event: events.SlideEvent) -> None:
        """Handler for SlideEvent updates."""
        presentation = self.presentation
        if presentation is None:
            print(
                f"\tTldraw: ignoring slide update since current presentation is not known"
            )
            return

        slide = event["slide"]
        if self.slide == slide:
            print("\tTldraw: slide did not change")
            return

        # Only keep cached shape patterns for the current presentation/slide
        self.shape_patterns.clear()

        self.slide = slide
        self.presentation_slide[presentation] = slide
        self.shapes_changed = True
        print(f"\tTldraw: presentation: {presentation}, slide: {slide}")

    def add_shape_event(self, event: tldraw.AddShapeEvent) -> None:
        """Handler for tldraw AddShapeEvent updates."""
        presentation = event["presentation"]
        slide = event["slide"]
        id = event["id"]
        data = event["data"]

        if "type" in data and data["type"] == "image":
            print(f"\tTldraw: ignoring image shape type: {id}")
            return

        self.ensure_shape_structure(presentation, slide)

        if id in self.shapes[presentation][slide]:
            shape = cast(Shape, self.shapes[presentation][slide][id])
            shape.update_from_data(data)
            action = "updated"
        else:
            if "type" in data:
                shape = parse_shape_from_data(data)
                self.shapes[presentation][slide][id] = shape
                action = "added"
            else:
                print(f'\tTldraw: Got add for shape: {id} with missing "type" field')
                return

        try:
            del self.shape_patterns[id]
        except KeyError:
            pass

        self.shapes_changed = True
        print(
            f"\tTldraw: {action} shape: {id}, presentation: {presentation}, slide: {slide}, {repr(shape)}"
        )

    def delete_shape_event(self, event: tldraw.DeleteShapeEvent) -> None:
        id = event["id"]
        presentation = event["presentation"]
        slide = event["slide"]

        try:
            del self.shapes[presentation][slide][id]
        except KeyError:
            return
        except ValueError:
            return

        try:
            del self.shape_patterns[id]
        except KeyError:
            pass

        self.shapes_changed = True
        print(
            f"\tTldraw: deleted shape: {id}, presentation: {presentation}, slide: {slide}"
        )

    def update(self, event: Event) -> None:
        if event["name"] == "presentation":
            self.presentation_event(cast(events.PresentationEvent, event))
        elif event["name"] == "slide":
            self.slide_event(cast(events.SlideEvent, event))
        elif event["name"] == "tldraw.add_shape":
            self.add_shape_event(cast(tldraw.AddShapeEvent, event))
        elif event["name"] == "tldraw.delete_shape":
            self.delete_shape_event(cast(tldraw.DeleteShapeEvent, event))

    def finalize_frame(self, transform: Transform) -> bool:
        transform_changed = self.transform != transform
        if not self.shapes_changed and not transform_changed:
            return False
        self.transform = transform
        presentation = self.presentation
        slide = self.slide
        if (
            presentation is None
            or slide is None
            or not presentation in self.shapes
            or not slide in self.shapes[presentation]
        ):
            self.pattern = None
            return False

        if transform_changed:
            self.shape_patterns.clear()

        shapes = self.shapes[presentation][slide]
        print(f"\tTldraw: Rendering {len(shapes)} shapes.")

        ctx = self.ctx
        ctx.push_group()

        apply_shapes_transform(ctx, transform)

        for id, s in shapes.items():
            shape = cast(Shape, s)
            if id in self.shape_patterns:
                print(f"\tTldraw: Cached {shape.__class__.__name__}: {id}")
            else:
                ctx.push_group()

                ctx.translate(*shape.point)
                if isinstance(shape, DrawShape):
                    finalize_draw(ctx, id, shape)
                elif isinstance(shape, RectangleShape):
                    finalize_rectangle(ctx, id, shape)
                elif isinstance(shape, TriangleShape):
                    finalize_triangle(ctx, id, shape)
                elif isinstance(shape, EllipseShape):
                    finalize_ellipse(ctx, id, shape)
                elif isinstance(shape, ArrowShape):
                    finalize_arrow(ctx, id, shape)
                elif isinstance(shape, TextShape):
                    finalize_text(ctx, id, shape)
                elif isinstance(shape, StickyShape):
                    finalize_sticky(ctx, shape)
                elif isinstance(shape, GroupShape):
                    # Nothing to do? All group-related updates seem to be propagated to the
                    # individual shapes in the group.
                    pass
                else:
                    print(f"\tTldraw: Don't know how to render {shape}")

                self.shape_patterns[id] = ctx.pop_group()

            ctx.set_source(self.shape_patterns[id])
            ctx.paint()

        self.pattern = ctx.pop_group()
        self.shapes_changed = False

        return True

    def render(self) -> None:
        if self.pattern is not None:
            ctx = self.ctx
            ctx.save()
            ctx.set_source(self.pattern)
            ctx.paint()
            ctx.restore()
