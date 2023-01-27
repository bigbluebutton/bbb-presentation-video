# SPDX-FileCopyrightText: 1999, 2004 Red Hat, Inc
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import cairo
from gi.repository import Pango

def context_set_font_options(
    context: Pango.Context, options: cairo.FontOptions
) -> None: ...
def create_context(cr: cairo.Context[cairo._SomeSurface]) -> Pango.Context: ...
def show_layout(
    cr: cairo.Context[cairo._SomeSurface], layout: Pango.Layout
) -> None: ...
