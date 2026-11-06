# SPDX-FileCopyrightText: 1999 The Free Software Foundation
#
# SPDX-License-Identifier: LGPL-2.0-or-later

from typing import Optional, Tuple, Union

class PixbufFormat: ...

class Pixbuf:
    @classmethod
    def new_from_file(cls, filename: Union[str, bytes]) -> Pixbuf: ...
    @classmethod
    def get_file_info(
        cls, filename: Union[str, bytes]
    ) -> Tuple[Optional[PixbufFormat], int, int]: ...
    def get_height(self) -> int: ...
    def get_width(self) -> int: ...
