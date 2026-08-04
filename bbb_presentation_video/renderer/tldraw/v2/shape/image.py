# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from os import path
from typing import Optional, TypeVar

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib

from bbb_presentation_video.renderer.tldraw.shape import ImageShape

CairoSomeSurface = TypeVar("CairoSomeSurface", bound=cairo.Surface)

IMAGE_EXTENSIONS = frozenset(("gif", "jpeg", "jpg", "png", "webp"))
"""Image types that can be pasted onto the whiteboard, matching the allowlist
used by bbb-export-annotations."""


def upload_filename(src: str) -> Optional[str]:
    """Resolve an image source to a file name within the uploads directory.

    Only the base name is kept, so a source crafted by a presenter cannot
    escape the uploads directory, and the extension has to be one that the
    whiteboard accepts.
    """
    filename = path.basename(src)
    extension = path.splitext(filename)[1][1:].lower()
    if extension not in IMAGE_EXTENSIONS:
        return None
    return filename


def load_pixbuf(shape: ImageShape, directory: str) -> Optional[GdkPixbuf.Pixbuf]:
    """Load the image belonging to a shape, caching the result on the shape.

    Recordings made before pasted images were archived have no uploads
    directory, so an image that cannot be read is reported and skipped instead
    of interrupting the rendering.
    """
    if shape.pixbuf_loaded:
        return shape.pixbuf
    shape.pixbuf_loaded = True

    if shape.src is None:
        return None

    filename = upload_filename(shape.src)
    if filename is None:
        print(f"\tTldraw: image has an unsupported source: {shape.src}")
        return None

    filepath = path.join(directory, "uploads", filename)
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
    except GLib.Error as error:
        print(f"\tTldraw: failed to read image {filepath}: {error}")
        return None

    if pixbuf.get_width() <= 0 or pixbuf.get_height() <= 0:
        print(f"\tTldraw: ignoring empty image {filepath}")
        return None

    shape.pixbuf = pixbuf
    return pixbuf


def finalize_image(
    ctx: cairo.Context[CairoSomeSurface],
    id: str,
    shape: ImageShape,
    directory: str,
) -> None:
    print(f"\tTldraw: Finalizing Image: {id}")

    pixbuf = load_pixbuf(shape, directory)
    if pixbuf is None:
        return

    if shape.size.width <= 0 or shape.size.height <= 0:
        print(f"\tTldraw: ignoring image with a degenerate size: {id}")
        return

    style = shape.style

    ctx.rotate(shape.rotation)

    ctx.push_group()

    # Draw at the image's own resolution and let cairo scale it to the size the
    # shape was given, so that zooming in does not resample twice.
    ctx.save()
    ctx.scale(
        shape.size.width / pixbuf.get_width(),
        shape.size.height / pixbuf.get_height(),
    )
    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
    ctx.rectangle(0, 0, pixbuf.get_width(), pixbuf.get_height())
    ctx.fill()
    ctx.restore()

    ctx.pop_group_to_source()
    ctx.paint_with_alpha(style.opacity)
