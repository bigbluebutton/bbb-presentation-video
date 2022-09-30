#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2022 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from sys import version

from setuptools import find_packages, setup

if version < "3":
    print("This package requires python3")
    exit(1)

setup(
    name="bbb-presentation-video",
    description="Render BigBlueButton recording events.xml file to a video",
    author="Calvin Walton",
    author_email="calvin.walton@kepstin.ca",
    license="LGPLv2+",
    version="3.0.4.1",
    install_requires=["lxml"],
    packages=find_packages(),
    entry_points={
        "console_scripts": ["bbb-presentation-video = bbb_presentation_video:main"]
    },
    package_data={"": ["*.pdf"]},
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Communications :: Conferencing",
        "Topic :: Multimedia :: Video :: Conversion",
    ],
)
