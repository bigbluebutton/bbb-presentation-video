# SPDX-FileCopyrightText: 1999, 2004 Red Hat, Inc
#
# SPDX-License-Identifier: LGPL-2.0-or-later

from typing import Optional

import cairo
from gi.repository import Pango

def context_set_font_options(
    context: Pango.Context, options: Optional[cairo.FontOptions]
) -> None:
    """Sets the font options used when rendering text with this context.

    These options override any options that :func:`update_context`
    derives from the target surface.

    :param options: A :class:`cairo.FontOptions` or `None` to unset
        any previously set options.
    """

def context_set_resolution(context: Pango.Context, dpi: float) -> None:
    """Sets the resolution for the context.

    This is a scale factor between points specified in a :class:`Pango.FontDescription`
    and Cairo units. The default value is 96, meaning that a 10 point font will
    be 13 units high. (10 * 96. / 72. = 13.3).

    Since: 1.10
    """

def create_context(cr: cairo.Context[cairo._SomeSurface]) -> Pango.Context:
    """Creates a context object set up to match the current transformation
    and target surface of the Cairo context.

    This context can then be
    used to create a layout using :meth:`Pango.Layout`.

    This function is a convenience function that creates a context using
    the default font map, then updates it to `cr`. If you just need to
    create a layout for use with `cr` and do not need to access :class:`Pango.Context`
    directly, you can use :func:`create_layout` instead.
    """

def layout_line_path(
    cr: cairo.Context[cairo._SomeSurface], line: Pango.LayoutLine
) -> None:
    """Adds the text in :class:`Pango.LayoutLine` to the current path in the specified cairo context.

    The origin of the glyphs (the left edge of the line) will be at the current point of the cairo context.

    Since: 1.10
    """

def show_layout(
    cr: cairo.Context[cairo._SomeSurface], layout: Pango.Layout
) -> None: ...
def show_layout_line(
    ct: cairo.Context[cairo._SomeSurface], line: Pango.LayoutLine
) -> None:
    """Draws a :class:`Pango.LayoutLine` in the specified cairo context.

    The origin of the glyphs (the left edge of the line) will
    be drawn at the current point of the cairo context.

    Since: 1.10
    """

def update_context(
    cr: cairo.Context[cairo._SomeSurface], context: Pango.Context
) -> None:
    """Updates a :class:`Pango.Context` previously created for use with Cairo to
    match the current transformation and target surface of a Cairo
    context.

    If any layouts have been created for the context, it's necessary
    to call :func:`Pango.Layout.context_changed` on those layouts.

    Since: 1.10
    """
    ...
