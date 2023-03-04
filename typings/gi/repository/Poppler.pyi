# SPDX-FileCopyrightText: 2004 Red Hat, Inc
# SPDX-FileCopyrightText: 2021 André Guerreiro <aguerreiro1985@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

from typing import Optional, Tuple

import cairo
from gi.repository import Gio

class Document:
    @classmethod
    def new_from_gfile(
        cls,
        file: Gio.File,
        password: Optional[str],
        cancellable: Optional[Gio.Cancellable],
    ) -> Document:
        """Creates a new #PopplerDocument reading the PDF contents from @file.
        Possible errors include those in the #POPPLER_ERROR and #G_FILE_ERROR
        domains."""
    @classmethod
    def new_from_file(cls, uri: str, password: Optional[str] = None) -> Document: ...
    def get_n_pages(self) -> int: ...
    def get_page(self, index: int) -> Optional[Page]: ...

class Page:
    def get_size(self) -> Tuple[float, float]: ...
    def render(self, cairo: cairo.Context[cairo._SomeSurface]) -> None: ...
