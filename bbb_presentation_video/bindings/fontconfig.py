# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import ctypes
from typing import Union, cast

fontconfig = ctypes.cdll.LoadLibrary("libfontconfig.so.1")
fontconfig.FcConfigAppFontAddDir.argtypes = (ctypes.c_void_p, ctypes.c_char_p)
fontconfig.FcConfigAppFontAddDir.restype = ctypes.c_int


class FontconfigError(Exception):
    pass


def app_font_add_dir(dir: Union[str, bytes]) -> None:
    """Add fonts from directory to font database in the current configuration."""
    if isinstance(dir, str):
        dir = dir.encode()
    if cast(int, fontconfig.FcConfigAppFontAddDir(None, dir)) != 1:
        raise FontconfigError()
