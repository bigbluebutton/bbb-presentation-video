# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import atexit
from contextlib import ExitStack
from importlib import resources
from os import path

from bbb_presentation_video.bindings import fontconfig

__fontconfig_app_font_dir_added = False


def add_fontconfig_app_font_dir() -> None:
    global __fontconfig_app_font_dir_added
    if __fontconfig_app_font_dir_added:
        return

    stack = ExitStack()

    font_dirs = set()
    for filename in resources.contents(__package__):
        if not filename.endswith(".ttf"):
            continue
        abspath = stack.enter_context(resources.path(__package__, filename))
        font_dirs.add(path.dirname(abspath))

    try:
        for dir in font_dirs:
            print(dir)
            fontconfig.app_font_add_dir(dir)
    except fontconfig.FontconfigError:
        stack.close()
        return

    atexit.register(stack.close)
    __fontconfig_app_font_dir_added = True
