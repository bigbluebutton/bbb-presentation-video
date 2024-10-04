# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import TypeVar

import cairo
from gi.repository import Pango, PangoCairo

from bbb_presentation_video.events.helpers import Color
from bbb_presentation_video.renderer.tldraw.shape import PollShape, apply_shape_rotation
from bbb_presentation_video.renderer.tldraw.utils import (
    V2_COLORS,
    V2_TEXT_COLOR,
    ColorStyle,
)

FONT_FAMILY = "Arial"
POLL_LINE_WIDTH = 2.0
POLL_FONT_SIZE = 18
POLL_VPADDING = 8.0
POLL_HPADDING = 8.0

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)


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

    ctx.set_line_join(cairo.LINE_JOIN_MITER)
    ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

    # Draw the background and poll outline
    half_lw = POLL_LINE_WIDTH / 2
    ctx.set_line_width(POLL_LINE_WIDTH)
    ctx.move_to(half_lw, half_lw)
    ctx.line_to(width - half_lw, half_lw)
    ctx.line_to(width - half_lw, height - half_lw)
    ctx.line_to(half_lw, height - half_lw)
    ctx.close_path()
    ctx.set_source_rgb(*color.semi)
    ctx.fill_preserve()
    ctx.set_source_rgb(*color.solid)
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
    for answer in shape.answers:
        layout.set_text(answer.key, -1)
        (label_width, _) = layout.get_pixel_size()
        if label_width > max_label_width:
            max_label_width = label_width
        percent: str
        if shape.numResponders > 0:
            percent = "{}%".format(
                int(float(answer.numVotes) / float(shape.numResponders) * 100)
            )
        else:
            percent = "0%"
        layout.set_text(percent, -1)
        (percent_width, _) = layout.get_pixel_size()
        if percent_width > max_percent_width:
            max_percent_width = percent_width

    max_label_width = min(max_label_width, width * 0.3)
    max_percent_width = min(max_percent_width, width * 0.3)

    title_height = 0.0
    if shape.questionText != "":
        title_height = POLL_FONT_SIZE + POLL_VPADDING

    bar_height = (height - POLL_VPADDING - title_height) / len(
        shape.answers
    ) - POLL_VPADDING
    bar_width = width - 4 * POLL_HPADDING - max_label_width - max_percent_width
    bar_x = 2 * POLL_HPADDING + max_label_width

    # All sizes are calculated, so draw the poll
    layout.set_ellipsize(Pango.EllipsizeMode.END)
    if shape.questionText != "":
        layout.set_width(int(width - 2 * POLL_HPADDING) * Pango.SCALE)
        layout.set_text(shape.questionText, -1)
        title_width, title_height = layout.get_pixel_size()
        ctx.move_to(
            (width - title_width) / 2,
            (POLL_FONT_SIZE - title_height) / 2 + POLL_VPADDING,
        )
        ctx.set_source_rgb(*V2_TEXT_COLOR)
        PangoCairo.show_layout(ctx, layout)

    for i, answer in enumerate(shape.answers):
        bar_y = (bar_height + POLL_VPADDING) * i + POLL_VPADDING + title_height
        if shape.numResponders > 0:
            result_ratio = float(answer.numVotes) / float(shape.numResponders)
        else:
            result_ratio = 0.0
        percent = "{}%".format(int(result_ratio * 100))

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
        ctx.set_source_rgb(*color.solid)
        ctx.fill_preserve()
        ctx.stroke()

        # Draw the label and percentage
        ctx.set_source_rgb(*V2_TEXT_COLOR)
        layout.set_width(int(max_label_width * Pango.SCALE))
        layout.set_text(answer.key, -1)
        label_width, label_height = layout.get_pixel_size()
        ctx.move_to(
            bar_x - POLL_HPADDING - label_width,
            bar_y + (bar_height - label_height) / 2,
        )
        PangoCairo.show_layout(ctx, layout)
        layout.set_width(int(max_percent_width * Pango.SCALE))
        layout.set_text(percent, -1)
        percent_width, percent_height = layout.get_pixel_size()
        ctx.move_to(
            width - POLL_HPADDING - percent_width,
            bar_y + (bar_height - percent_height) / 2,
        )
        PangoCairo.show_layout(ctx, layout)

        # Draw the result count
        layout.set_ellipsize(Pango.EllipsizeMode.NONE)
        layout.set_width(-1)
        layout.set_text(str(answer.numVotes), -1)
        votes_width, votes_height = layout.get_pixel_size()
        if votes_width < (bar_x2 - bar_x - 2 * POLL_HPADDING):
            # Votes fit in the bar
            ctx.move_to(
                bar_x + (bar_x2 - bar_x - votes_width) / 2,
                bar_y + (bar_height - votes_height) / 2,
            )
            ctx.set_source_rgb(*color.semi)
            PangoCairo.show_layout(ctx, layout)
        else:
            # Votes do not fit in the bar, so put them after
            ctx.move_to(bar_x2 + POLL_HPADDING, bar_y + (bar_height - votes_height) / 2)
            ctx.set_source_rgb(*V2_TEXT_COLOR)
            PangoCairo.show_layout(ctx, layout)
