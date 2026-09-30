# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Render the tldraw ``poll`` shape.

The BigBlueButton client and bbb-playback draw this shape with a recharts
``<BarChart layout="vertical">`` inside a bordered box (``PollShapeUtil.tsx``
and ``poll-content.tsx`` in ``@bigbluebutton/tldraw``). The layout below mirrors
that component and the recharts defaults it relies on, so the video recording
format shows the same chart as the live session and the presentation format.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import TypeVar

import cairo
from gi.repository import Pango, PangoCairo

from bbb_presentation_video.events.helpers import Color, Size
from bbb_presentation_video.renderer.tldraw.recharts_scale import get_nice_tick_values
from bbb_presentation_video.renderer.tldraw.shape import (
    PollShape,
    apply_shape_rotation,
)
from bbb_presentation_video.renderer.tldraw.utils import (
    V2_COLORS,
    V2_TEXT_COLOR,
    ColorStyle,
    rounded_rect,
    rounded_rect_shadow,
)

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)

FONT_FAMILY = "Arial"

# Shape container: PollShapeUtil.tsx <HTMLContainer style={...}>
BORDER_COLOR = Color.from_int(0x8B9AA8)
BORDER_WIDTH = 1.0
BORDER_RADIUS = 4.0
# box-shadow: 0px 0px 4px 0px rgba(0, 0, 0, 0.20)
SHADOW_BLUR = 4.0
SHADOW_ALPHA = 0.2

# Question text: styles.ts PollText
TITLE_FONT_SIZE = 20.0  # 1.25rem
TITLE_MARGIN_TOP = 8.0  # 0.5rem
TITLE_MARGIN_BOTTOM = 8.0  # 0.5rem
TITLE_MARGIN_LEFT = 44.0  # 2.75rem
# PollShapeUtil.tsx: adjustedHeight = height - 75 when there is a question
TITLE_RESERVED_HEIGHT = 75.0

# Chart: poll-content.tsx and recharts defaults
CHART_WIDTH_RATIO = 0.9  # <ResponsiveContainer width="90%">
CHART_MARGIN = 5.0  # BarChart default margin, every side
X_AXIS_HEIGHT = 30.0  # XAxis default height
Y_AXIS_WIDTH = 80.0  # <YAxis width={80}>; half the shape width for typed polls
X_AXIS_TICK_COUNT = 5  # XAxis default tickCount
TICK_SIZE = 6.0  # recharts default tickSize
TICK_MARGIN = 2.0  # recharts default tickMargin
TICK_FONT_SIZE = 12.0  # inherited from .tl-container
TICK_LABEL_DY = 0.71  # recharts puts bottom tick labels at dy="0.71em"
AXIS_COLOR = Color.from_int(0x666666)
BAR_COLOR = Color.from_int(0x0C57A7)
BAR_CATEGORY_GAP = 0.1  # recharts default barCategoryGap "10%"
LABEL_ELLIPSIS = "..."
# CustomizedAxisTick.tsx measures "0" on a canvas whose font assignment is not
# a valid CSS font shorthand, so the browser default canvas font (10px) applies
LABEL_MEASURE_FONT_SIZE = 10.0
# The client prefixes correct quiz answers with an emoji check mark; use a
# glyph that the fonts shipped with this package can render
CORRECT_ANSWER_MARK = "✔ "


def truncate_label(label: str, axis_width: float, char_width: float) -> str:
    """Shorten a category label the way CustomizedAxisTick.tsx does."""
    max_chars = math.floor((axis_width - TICK_SIZE) / char_width)
    if len(label) <= max_chars:
        return label
    return label[: max(max_chars - len(LABEL_ELLIPSIS), 0)] + LABEL_ELLIPSIS


def text_layout(
    ctx: cairo.Context[CairoSomeSurface],
    size: float,
    weight: Pango.Weight = Pango.Weight.NORMAL,
) -> Pango.Layout:
    font = Pango.FontDescription()
    font.set_family(FONT_FAMILY)
    font.set_absolute_size(int(size * Pango.SCALE))
    font.set_weight(weight)
    layout = Pango.Layout(PangoCairo.create_context(ctx))
    layout.set_font_description(font)
    return layout


def draw_container(
    ctx: cairo.Context[CairoSomeSurface], size: Size, fill: Color
) -> None:
    # Shadow. Doing blurred shadow is hard, so this is a two-layer drop shadow instead
    rounded_rect_shadow(ctx, size, BORDER_RADIUS, SHADOW_ALPHA / 8, spread=SHADOW_BLUR)
    rounded_rect_shadow(
        ctx, size, BORDER_RADIUS, SHADOW_ALPHA / 4, spread=SHADOW_BLUR / 2
    )

    rounded_rect(ctx, size, BORDER_RADIUS)
    ctx.set_source_rgb(*fill)
    ctx.fill()

    # The border is drawn inside the box
    half_bw = BORDER_WIDTH / 2
    ctx.save()
    ctx.translate(half_bw, half_bw)
    rounded_rect(
        ctx,
        Size(size.width - BORDER_WIDTH, size.height - BORDER_WIDTH),
        BORDER_RADIUS - half_bw,
    )
    ctx.restore()
    ctx.set_line_width(BORDER_WIDTH)
    ctx.set_source_rgb(*BORDER_COLOR)
    ctx.stroke()


def draw_chart(
    ctx: cairo.Context[CairoSomeSurface],
    shape: PollShape,
    x: float,
    y: float,
    width: float,
    height: float,
    shape_width: float,
) -> None:
    is_typed_poll = shape.questionType.startswith("R-")
    y_axis_width = math.floor(shape_width / 2) if is_typed_poll else Y_AXIS_WIDTH
    plot_left = x + CHART_MARGIN + y_axis_width
    plot_right = x + width - CHART_MARGIN
    plot_top = y + CHART_MARGIN
    plot_bottom = y + height - CHART_MARGIN - X_AXIS_HEIGHT
    if plot_right <= plot_left or plot_bottom <= plot_top:
        return

    answers = shape.answers
    max_votes = max(answer.numVotes for answer in answers)
    ticks = get_nice_tick_values(
        (0, max_votes), X_AXIS_TICK_COUNT, allow_decimals=False
    )
    domain_min = min(ticks)
    domain_max = max(ticks)

    def value_x(value: float) -> float:
        if domain_max == domain_min:
            return plot_left
        ratio = float((Decimal(value) - domain_min) / (domain_max - domain_min))
        return plot_left + ratio * (plot_right - plot_left)

    band = (plot_bottom - plot_top) / len(answers)

    # Axes and tick marks
    ctx.set_line_width(1.0)
    ctx.set_source_rgb(*AXIS_COLOR)
    ctx.move_to(plot_left, plot_bottom)
    ctx.line_to(plot_right, plot_bottom)
    ctx.move_to(plot_left, plot_top)
    ctx.line_to(plot_left, plot_bottom)
    for tick in ticks:
        tick_x = value_x(float(tick))
        ctx.move_to(tick_x, plot_bottom)
        ctx.line_to(tick_x, plot_bottom + TICK_SIZE)
    for index in range(len(answers)):
        center_y = plot_top + band * (index + 0.5)
        ctx.move_to(plot_left - TICK_SIZE, center_y)
        ctx.line_to(plot_left, center_y)
    ctx.stroke()

    # Tick labels on the numeric axis, centered on their tick. Like the SVG text
    # elements of the client, the labels are positioned by their baseline.
    tick_layout = text_layout(ctx, TICK_FONT_SIZE)
    tick_baseline = (
        plot_bottom + TICK_SIZE + TICK_MARGIN + TICK_LABEL_DY * TICK_FONT_SIZE
    )
    for tick in ticks:
        tick_layout.set_text(f"{tick.normalize():f}", -1)
        tick_width, _ = tick_layout.get_pixel_size()
        ctx.move_to(
            value_x(float(tick)) - tick_width / 2,
            tick_baseline - tick_layout.get_baseline() / Pango.SCALE,
        )
        PangoCairo.show_layout(ctx, tick_layout)

    # Category labels, ending at their tick; the client's tick component ignores
    # verticalAnchor, so the baseline sits on the band center
    measure_layout = text_layout(ctx, LABEL_MEASURE_FONT_SIZE)
    measure_layout.set_text("0", -1)
    char_width = measure_layout.get_size()[0] / Pango.SCALE or 6.0
    label_layout = text_layout(ctx, TICK_FONT_SIZE)
    for index, answer in enumerate(answers):
        label = (CORRECT_ANSWER_MARK if answer.isCorrectAnswer else "") + answer.key
        label_layout.set_text(truncate_label(label, y_axis_width, char_width), -1)
        label_width, _ = label_layout.get_pixel_size()
        ctx.move_to(
            plot_left - TICK_SIZE - TICK_MARGIN - label_width,
            plot_top + band * (index + 0.5) - label_layout.get_baseline() / Pango.SCALE,
        )
        PangoCairo.show_layout(ctx, label_layout)

    # Bars
    bar_offset = band * BAR_CATEGORY_GAP
    bar_height = band - 2 * bar_offset
    ctx.set_source_rgb(*BAR_COLOR)
    for index, answer in enumerate(answers):
        bar_width = value_x(answer.numVotes) - plot_left
        if bar_width <= 0:
            continue
        ctx.rectangle(
            plot_left, plot_top + band * index + bar_offset, bar_width, bar_height
        )
        ctx.fill()


def finalize_poll(
    ctx: cairo.Context[CairoSomeSurface], id: str, shape: PollShape
) -> None:
    print(f"\tTldraw: Finalizing Poll: {id}")

    if len(shape.answers) == 0:
        return

    apply_shape_rotation(ctx, shape)

    width = shape.size.width
    height = shape.size.height
    color = V2_COLORS.get(shape.style.color, V2_COLORS[ColorStyle.BLACK])

    draw_container(ctx, shape.size, color.semi)

    # The content box sits inside the border and clips its children
    ctx.save()
    ctx.rectangle(0, BORDER_WIDTH, width, height - 2 * BORDER_WIDTH)
    ctx.clip()

    # The title's top margin collapses through its wrapper, so the content
    # starts one margin below the border even when there is no question
    content_top = BORDER_WIDTH + TITLE_MARGIN_TOP
    if shape.questionText != "":
        title_layout = text_layout(ctx, TITLE_FONT_SIZE, Pango.Weight.MEDIUM)
        title_layout.set_width(int((width - TITLE_MARGIN_LEFT) * Pango.SCALE))
        title_layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        title_layout.set_text(shape.questionText, -1)
        _, title_height = title_layout.get_pixel_size()
        ctx.move_to(TITLE_MARGIN_LEFT, content_top)
        ctx.set_source_rgb(*V2_TEXT_COLOR)
        PangoCairo.show_layout(ctx, title_layout)
        chart_top = content_top + title_height + TITLE_MARGIN_BOTTOM
        chart_height = height - TITLE_RESERVED_HEIGHT
    else:
        chart_top = content_top
        chart_height = height

    if chart_height > 0:
        draw_chart(
            ctx,
            shape,
            x=0,
            y=chart_top,
            width=width * CHART_WIDTH_RATIO,
            height=chart_height,
            shape_width=width,
        )

    ctx.restore()
