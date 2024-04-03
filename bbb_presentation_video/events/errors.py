# SPDX-FileCopyrightText: 2024 BigBlueButton Inc. and by respective authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional


class EventParsingError(Exception):
    eventname: str
    reason: str

    def __init__(self, eventname: str, reason: Optional[str] = None):
        self.eventname = eventname
        self.reason = reason or "Unspecified error"

    def __str__(self) -> str:
        return f"Failed to parse event {self.eventname}: {self.reason}"


class UnknownEventError(EventParsingError):
    def __init__(self, eventname: str):
        super().__init__(eventname, "Unknown event.")


class UnknownShapeError(EventParsingError):
    def __init__(self, eventname: str, shape: str):
        super().__init__(eventname, f"Unknown shape '{shape}'")


class InvalidShapeError(EventParsingError):
    shape: str
    status: str
    reason: str

    def __init__(self, eventname: str, shape: str, status: str, reason: str):
        super().__init__(eventname)
        self.shape = shape
        self.status = status
        self.reason = reason

    def __str__(self) -> str:
        return f"Shape {self.shape} in {self.eventname} with status {self.status} is invalid: {self.reason}"


class ShapeNoDataPointsError(InvalidShapeError):
    def __init__(self, eventname: str, shape: str, status: str):
        super().__init__(eventname, shape, status, "no dataPoints")
