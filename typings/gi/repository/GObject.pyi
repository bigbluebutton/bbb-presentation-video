# SPDX-FileCopyrightText: 1998-1999, 2000-2001 Tim Janik and Red Hat, Inc.
#
# SPDX-License-Identifier: LGPL-2.1-or-later

class Object:
    """The base object type.

    All the fields in the `GObject` structure are private to the implementation
    and should never be accessed directly.

    Since GLib 2.72, all #GObjects are guaranteed to be aligned to at least the
    alignment of the largest basic GLib type (typically this is #guint64 or
    #gdouble). If you need larger alignment for an element in a #GObject, you
    should allocate it on the heap (aligned), or arrange for your #GObject to be
    appropriately padded. This guarantee applies to the #GObject (or derived)
    struct, the #GObjectClass (or derived) struct, and any private data allocated
    by G_ADD_PRIVATE().
    """
