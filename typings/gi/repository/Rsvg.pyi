# SPDX-FileCopyrightText: 2000 Eazel, Inc.
#
# SPDX-License-Identifier: LGPL-2.1-or-later

from typing import Optional, Tuple

import cairo

class Rectangle:
    x: float
    y: float
    width: float
    height: float

class Handle:
    @classmethod
    def new_from_file(cls, file_name: str) -> Optional[Handle]:
        """Loads the SVG specified by @file_name."""

    def get_intrinsic_size_in_pixels(self) -> Tuple[bool, float, float]:
        """Converts an SVG document's intrinsic dimensions to pixels.

        Returns whether the document has both width and height in pixel units,
        followed by those dimensions."""

    def render_document(
        self, cr: cairo.Context[cairo._SomeSurface], viewport: Rectangle
    ) -> bool:
        """Renders the whole SVG document fitted to a viewport."""
