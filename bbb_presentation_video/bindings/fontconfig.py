# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import ctypes
from ctypes import c_char_p, c_int, c_void_p
from typing import Any, Optional, Tuple, Type, Union, cast


class FontconfigError(Exception):
    pass


def _FcBool_errcheck(
    result: Optional[Type[ctypes._CData]],
    _func: ctypes._FuncPointer,
    _arguments: Tuple[ctypes._CData, ...],
) -> Any:
    res = int(cast(c_int, result))
    if res != 1:
        raise FontconfigError()


fontconfig = ctypes.cdll.LoadLibrary("libfontconfig.so.1")
fontconfig.FcConfigAppFontAddDir.argtypes = (c_void_p, c_char_p)
fontconfig.FcConfigAppFontAddDir.restype = c_int
fontconfig.FcConfigAppFontAddDir.errcheck = _FcBool_errcheck


def app_font_add_dir(dir: Union[str, bytes]) -> None:
    """Add fonts from directory to font database in the current configuration."""
    if isinstance(dir, str):
        dir = dir.encode()
    fontconfig.FcConfigAppFontAddDir(None, dir)
