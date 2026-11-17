# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Stable per-page identity for the events of a recording.

A page number is not a stable name for a page. Inserting pages into a shared
presentation renumbers every page at and after the insert position, so the same
number can refer to two different pages at two points in the same recording.
Anything remembered per page - annotations, cursor positions, which background
to draw - therefore has to be keyed by the page's opaque id instead.

Recordings carry that id in two places: on the events themselves (``id`` on
GotoSlideEvent, ``whiteboardId`` on the whiteboard events) and in the
``pages.json`` manifest written next to the slide files. Recordings made before
either existed get a composite key built from the page number, which behaves
exactly like the per-number bookkeeping it replaces.

This mirrors ``page_identity_key``/``learn_page_key`` in the publish script
(record-and-playback/presentation/scripts/publish/presentation.rb), so the
video and the presentation playback agree on what a page is.
"""

from __future__ import annotations

import json
from os import path
from typing import Dict, Optional, Tuple


def read_page_id_manifest(presentation_dir: str) -> Dict[int, str]:
    """Read the page number to page id manifest written by the conversion pipeline.

    Returns an empty mapping for recordings made before the manifest existed.
    """
    manifest_file = f"{presentation_dir}/pages.json"
    if not path.exists(manifest_file):
        return {}
    try:
        with open(manifest_file, "r", encoding="utf-8") as file:
            manifest = json.load(file)
        return {int(number): str(page_id) for number, page_id in manifest.items()}
    except (OSError, ValueError, AttributeError) as error:
        print(f"Ignoring unreadable page id manifest {manifest_file}: {error}")
        return {}


class PageKeyResolver:
    """Resolves the stable identity of the page an event refers to."""

    directory: str
    manifests: Dict[str, Dict[int, str]]
    learned: Dict[Tuple[str, int], str]

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.manifests = {}
        self.learned = {}

    def manifest(self, presentation: str) -> Dict[int, str]:
        if presentation not in self.manifests:
            self.manifests[presentation] = read_page_id_manifest(
                f"{self.directory}/presentation/{presentation}"
            )
        return self.manifests[presentation]

    def learn(
        self, presentation: Optional[str], slide: int, page_id: Optional[str]
    ) -> None:
        """Remember an id seen on an event, for pages that never carry one.

        The page shown when a recording starts has no GotoSlideEvent of its own,
        but the annotations drawn on it name it, so the id can be borrowed from
        them. This assumes a page number refers to the same page for the whole
        recording, which inserts break - recordings that can contain an insert
        also have a manifest, which is consulted first.
        """
        if not page_id:
            return
        self.learned.setdefault((presentation or "", slide), page_id)

    def resolve(
        self, presentation: Optional[str], slide: int, page_id: Optional[str] = None
    ) -> str:
        """Name the page an event acts on.

        The presentation is unknown for events that happen before one is shared;
        those still get a key, so that every page-scoped event has one, but it
        can only be built from the page number.
        """
        if page_id:
            return page_id
        if presentation is not None:
            # Manifest page numbers are 1-based, event numbers are 0-based.
            manifest_id = self.manifest(presentation).get(slide + 1)
            if manifest_id:
                return manifest_id
        learned = self.learned.get((presentation or "", slide))
        if learned:
            return learned
        # Matches the composite ids recorded by BBB versions where the
        # whiteboardId was "<presentationId>/<pageNum>".
        return f"{presentation or ''}/{slide + 1}"
