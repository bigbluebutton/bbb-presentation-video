# SPDX-FileCopyrightText: 1995-1997 Peter Mattis, Spencer Kimball and Josh MacDonald
# SPDX-FileCopyrightText: 2005 Red Hat, Inc.
#
# SPDX-License-Identifier: LGPL-2.0-or-later

import cairo
from gi.repository import GdkPixbuf

def cairo_set_source_pixbuf(
    cr: cairo.Context[cairo._SomeSurface],
    pixbuf: GdkPixbuf.Pixbuf,
    pixbuf_x: float,
    pixbuf_y: float,
) -> None: ...
