"""Gio is a library providing useful classes for general purpose I/O, networking, IPC,
settings, and other high level application functionality
"""

from gi.repository import GObject

# Classes

class Cancellable(GObject.Object):
    """GCancellable is a thread-safe operation cancellation stack used
    throughout GIO to allow for cancellation of synchronous and
    asynchronous operations."""

# Interfaces

class File(GObject.Object):
    """GFile is a high level abstraction for manipulating files on a virtual file
    system.

    GFiles are lightweight, immutable objects that do no I/O upon creation. It is
    necessary to understand that GFile objects do not represent files, merely an
    identifier for a file. All file content I/O is implemented as streaming operations
    (see GInputStream and GOutputStream).
    """

    @classmethod
    def new_for_path(cls, path: str | bytes) -> File:
        """Constructs a GFile for a given path. This operation never fails, but the
        returned object might not support any I/O operation if path is malformed.
        """
