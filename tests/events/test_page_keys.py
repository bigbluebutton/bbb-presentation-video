# SPDX-FileCopyrightText: 2026 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List

from bbb_presentation_video.events import Event, resolve_page_keys
from bbb_presentation_video.events.page_keys import (
    PageKeyResolver,
    read_page_id_manifest,
)

PRESENTATION = "pres-1"
PAGE_1 = "e0c1a3aa-0000-0000-0000-000000000001"
PAGE_2 = "e0c1a3aa-0000-0000-0000-000000000002"
INSERTED = "e0c1a3aa-0000-0000-0000-00000000000f"


def write_manifest(directory: Path, pages: Dict[str, str]) -> None:
    presentation_dir = directory / "presentation" / PRESENTATION
    presentation_dir.mkdir(parents=True, exist_ok=True)
    (presentation_dir / "pages.json").write_text(json.dumps(pages))


def test_read_manifest_keys_are_numbers(tmp_path: Path) -> None:
    write_manifest(tmp_path, {"1": PAGE_1, "2": PAGE_2})
    manifest = read_page_id_manifest(str(tmp_path / "presentation" / PRESENTATION))
    assert manifest == {1: PAGE_1, 2: PAGE_2}


def test_read_manifest_missing_is_empty(tmp_path: Path) -> None:
    assert read_page_id_manifest(str(tmp_path / "nowhere")) == {}


def test_read_manifest_unparseable_is_empty(tmp_path: Path) -> None:
    presentation_dir = tmp_path / "presentation" / PRESENTATION
    presentation_dir.mkdir(parents=True)
    (presentation_dir / "pages.json").write_text("{not json")
    assert read_page_id_manifest(str(presentation_dir)) == {}


def test_resolve_prefers_the_id_on_the_event(tmp_path: Path) -> None:
    write_manifest(tmp_path, {"1": PAGE_1})
    resolver = PageKeyResolver(str(tmp_path))
    assert resolver.resolve(PRESENTATION, 0, INSERTED) == INSERTED


def test_resolve_falls_back_to_the_manifest(tmp_path: Path) -> None:
    write_manifest(tmp_path, {"1": PAGE_1, "2": PAGE_2})
    resolver = PageKeyResolver(str(tmp_path))
    # Event page numbers are 0-based, manifest page numbers are 1-based.
    assert resolver.resolve(PRESENTATION, 0) == PAGE_1
    assert resolver.resolve(PRESENTATION, 1) == PAGE_2


def test_resolve_falls_back_to_a_learned_id(tmp_path: Path) -> None:
    resolver = PageKeyResolver(str(tmp_path))
    resolver.learn(PRESENTATION, 0, PAGE_1)
    assert resolver.resolve(PRESENTATION, 0) == PAGE_1


def test_learn_keeps_the_first_id_and_ignores_empty(tmp_path: Path) -> None:
    resolver = PageKeyResolver(str(tmp_path))
    resolver.learn(PRESENTATION, 0, None)
    resolver.learn(PRESENTATION, 0, "")
    resolver.learn(PRESENTATION, 0, PAGE_1)
    resolver.learn(PRESENTATION, 0, PAGE_2)
    assert resolver.resolve(PRESENTATION, 0) == PAGE_1


def test_resolve_falls_back_to_a_composite_key(tmp_path: Path) -> None:
    resolver = PageKeyResolver(str(tmp_path))
    # 1-based, matching the whiteboardId of recordings that had no page ids.
    assert resolver.resolve(PRESENTATION, 0) == f"{PRESENTATION}/1"
    assert resolver.resolve(PRESENTATION, 4) == f"{PRESENTATION}/5"


def test_resolve_without_a_presentation(tmp_path: Path) -> None:
    resolver = PageKeyResolver(str(tmp_path))
    assert resolver.resolve(None, 0) == "/1"


def event(name: str, **fields: Any) -> Event:
    parsed: Dict[str, Any] = {"name": name, "timestamp": Fraction(0)}
    parsed.update(fields)
    return parsed  # type: ignore[return-value]


def keys_of(events: List[Event]) -> List[Any]:
    return [e.get("page_key") for e in events]  # type: ignore[attr-defined]


def test_inserted_page_does_not_share_a_key_with_the_page_it_displaced(
    tmp_path: Path,
) -> None:
    """A page number is reused after an insert; the pages behind it are not.

    Page 2 of the presentation is annotated, a page is then inserted in front of
    it and annotated in turn. Both sets of annotations arrive under page number
    1, and must not end up on the same page.
    """
    write_manifest(tmp_path, {"1": PAGE_1, "2": INSERTED, "3": PAGE_2})
    events: List[Event] = [
        event("presentation", presentation=PRESENTATION),
        event("slide", slide=1, page_id=PAGE_2),
        event("tldraw.add_shape", presentation=PRESENTATION, slide=1, page_id=PAGE_2),
        # The insert renumbers: page number 1 is now the inserted page.
        event("slide", slide=1, page_id=INSERTED),
        event("tldraw.add_shape", presentation=PRESENTATION, slide=1, page_id=INSERTED),
        # Back to the original page, which has moved to number 2.
        event("slide", slide=2, page_id=PAGE_2),
    ]

    resolve_page_keys(events, str(tmp_path))

    assert keys_of(events) == [PAGE_1, PAGE_2, PAGE_2, INSERTED, INSERTED, PAGE_2]


def test_page_shown_at_the_start_is_named_by_its_annotations(tmp_path: Path) -> None:
    """The first page has no slide event of its own, but its shapes name it."""
    events: List[Event] = [
        event("presentation", presentation=PRESENTATION),
        event("tldraw.add_shape", presentation=PRESENTATION, slide=0, page_id=PAGE_1),
    ]

    resolve_page_keys(events, str(tmp_path))

    # No manifest here, so the presentation event has to borrow the id that the
    # shape event carries, or the two would be on different pages.
    assert keys_of(events) == [PAGE_1, PAGE_1]


def test_returning_to_a_presentation_restores_its_page(tmp_path: Path) -> None:
    """Sharing a presentation again returns to its last viewed page.

    The renderers restore that page, so an event that names no page of its own
    right after the switch must resolve against it, not against the page the
    previous presentation was left on.
    """
    events: List[Event] = [
        event("presentation", presentation="pres-a"),
        event("slide", slide=2, page_id=None),
        event("presentation", presentation="pres-b"),
        event("cursor_v2", page_id=None),
        event("presentation", presentation="pres-a"),
        event("cursor_v2", page_id=None),
    ]

    resolve_page_keys(events, str(tmp_path))

    assert keys_of(events) == [
        "pres-a/1",
        "pres-a/3",
        # pres-b has never been shown, so it opens on its first page.
        "pres-b/1",
        "pres-b/1",
        # pres-a returns on the page it was left on.
        "pres-a/3",
        "pres-a/3",
    ]


def test_recording_without_page_ids_keys_by_number(tmp_path: Path) -> None:
    """Older recordings carry no ids anywhere and keep per-number behaviour."""
    events: List[Event] = [
        event("presentation", presentation=PRESENTATION),
        event("slide", slide=1, page_id=None),
        event("shape", presentation=PRESENTATION, slide=1, page_id=None),
        event("shape", presentation=PRESENTATION, slide=None, page_id=None),
        event("slide", slide=2, page_id=None),
        event("shape", presentation=PRESENTATION, slide=2, page_id=None),
    ]

    resolve_page_keys(events, str(tmp_path))

    assert keys_of(events) == [
        f"{PRESENTATION}/1",
        f"{PRESENTATION}/2",
        f"{PRESENTATION}/2",
        # No page number of its own: the page being shown at the time.
        f"{PRESENTATION}/2",
        f"{PRESENTATION}/3",
        f"{PRESENTATION}/3",
    ]
