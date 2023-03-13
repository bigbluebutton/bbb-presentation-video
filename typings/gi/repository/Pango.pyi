# SPDX-FileCopyrightText: 1999 Red Hat Software
#
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Internationalized text layout and rendering"""

from enum import Enum
from typing import Optional, Tuple

from gi.repository import GObject

SCALE: int
"""The scale between dimensions used for Pango distances and device units.

The definition of device units is dependent on the output device; it will
typically be pixels for a screen, and points for a printer. `Pango.SCALE` is
currently 1024, but this may be changed in the future.

When setting font sizes, device units are always considered to be points (as
in "12 point font"), rather than pixels.
"""

class Context(GObject.Object):
    def get_base_dir(self) -> Direction:
        """Retrieves the base direction for the context."""
    def get_metrics(
        self, desc: FontDescription, language: Optional[Language]
    ) -> FontMetrics:
        """Get overall metric information for a particular font description.

        Since the metrics may be substantially different for different scripts,
        a language tag can be provided to indicate that the metrics should be
        retrieved that correspond to the script(s) used by that language.

        The :class:`Pango.FontDescription` is interpreted in the same way as by :func:`Pango.itemize`,
        and the family name may be a comma separated list of names. If characters
        from multiple of these families would be used to render the string, then
        the returned fonts would be a composite of the metrics for the fonts loaded
        for the individual families.
        """
    def set_base_dir(self, direction: Direction) -> None:
        """Sets the base direction for the context.

        The base direction is used in applying the Unicode bidirectional algorithm; if
        the direction is :const:`Pango.Direction.LTR` or :const:`Pango.Direction.RTL`,
        then the value will be used as the paragraph direction in the Unicode
        bidirectional algorithm. A value of :const:`Pango.Direction.WEAK_LTR` or
        :const:`Pango.Direction.WEAK_RTL` is used only for paragraphs that do not
        contain any strong characters themselves.
        """
    def set_round_glyph_positions(self, round_positions: bool) -> None:
        """Sets whether font rendering with this context should
        round glyph positions and widths to integral positions,
        in device units.

        This is useful when the renderer can't handle subpixel
        positioning of glyphs.

        The default value is to round glyph positions, to remain
        compatible with previous Pango behavior.

        Since: 1.44
        """
        ...

class Layout(GObject.Object):
    def __init__(self, context: Context):
        """Create a new :class:`Pango.Layout` object with attributes initialized to
        default values for a particular :class:`Pango.Context`.
        """
    def context_changed(self) -> None:
        """Forces recomputation of any state in the :class:`Pango.Layout` that
        might depend on the layout's context.

        This function should be called if you make changes to the context
        subsequent to creating the layout.
        """
    def get_alignment(self) -> Alignment:
        """Gets the alignment for the layout: how partial lines are positioned within
        the horizontal space available.
        """
    def get_auto_dir(self) -> bool:
        """Gets whether to calculate the base direction for the layout according to its
        contents.
        """
    def get_baseline(self) -> int:
        """Gets the Y position of baseline of the first line in `self`"""
    def get_context(self) -> Context:
        """Retrieves the :class:`Pango.Context` used for this layout."""
    def get_extents(self) -> Tuple[Rectangle, Rectangle]: ...
    def get_font_description(self) -> FontDescription:
        """Gets the font description for the layout, if any.

        Since: 1.8
        """
    def get_iter(self) -> LayoutIter:
        """Returns an iterator to iterate over the visual extents of the layout."""
    def get_line_count(self) -> int:
        """Retrieves the count of lines for `self`."""
    def get_lines_readonly(self) -> list[LayoutLine]:
        """Returns the lines of the @layout as a list.

        This is a faster alternative to :meth:`Pango.Layout.get_lines`,
        but the user is not expected to modify the contents of the lines
        (glyphs, glyph widths, etc.).

        Since: 1.16

        :returns:
            a list
            containing the lines in the layout. This points to internal data of the
            :class:`Pango.Layout` and must be used with care. It will become invalid on any
            change to the layout's text or properties. No changes should be made to
            the lines.
        """
    def get_pixel_size(self) -> Tuple[int, int]: ...
    def get_size(self) -> Tuple[int, int]:
        """Determines the logical width and height of a :class:`Pango.Layout` in Pango units.

        This is simply a convenience function around :meth:`Pango.Layout.get_extents()`.
        """
    def get_spacing(self) -> int: ...
    def get_width(self) -> int:
        """Gets the width to which the lines of the :class:`Pango.Layout` should wrap."""
    def set_alignment(self, alignment: Alignment) -> None:
        """Sets the alignment for the layout: how partial lines are
        positioned within the horizontal space available.

        The default alignment is :const:`Pango.Alignment.LEFT`.
        """
    def set_attributes(self, attrs: AttrList) -> None:
        """Sets the text attributes for a layout object."""
    def set_auto_dir(self, auto_dir: bool) -> None:
        """Sets whether to calculate the base direction
        for the layout according to its contents.

        When this flag is on (the default), then paragraphs in `self` that
        begin with strong right-to-left characters (Arabic and Hebrew principally),
        will have right-to-left layout, paragraphs with letters from other scripts
        will have left-to-right layout. Paragraphs with only neutral characters
        get their direction from the surrounding paragraphs.

        When `False`, the choice between left-to-right and right-to-left
        layout is done according to the base direction of the layout's
        :class:`Pango.Context`. (See :meth:`Pango.Context.set_base_dir`).

        When the auto-computed direction of a paragraph differs from the
        base direction of the context, the interpretation of
        :const:`Pango.Alignment.LEFT` and :const:`Pango.Alignment.RIGHT` are swapped.

        Since: 1.4
        """
    def set_ellipsize(self, ellipsize: EllipsizeMode) -> None: ...
    def set_font_description(self, desc: FontDescription) -> None:
        """Sets the default font description for the layout.

        If no font description is set on the layout, the
        font description from the layout's context is used.
        """
    def set_height(self, height: int) -> None: ...
    def set_justify(self, justify: bool) -> None: ...
    def set_line_spacing(self, factor: float) -> None: ...
    def set_spacing(self, spacing: int) -> None: ...
    def set_text(self, text: str, length: int) -> None:
        """Sets the text of the layout.

        This function validates `text` and renders invalid UTF-8
        with a placeholder glyph.

        Note that if you have used :meth:`Pango.Layout.set_markup` or
        :meth:`Pango.Layout.set_markup_with_accel` on the layout before, you
        may want to call :meth:`Pango.Layout.set_attributes` to clear the
        attributes set on the layout from the markup as this function does
        not clear attributes.

        :param text:
            the text
        :param length:
            maximum length of `text`, in bytes. -1 indicates that
            the string is nul-terminated and the length should be calculated.
            The text will also be truncated on encountering a nul-termination
            even when `length` is positive.
        """
    def set_width(self, width: int) -> None:
        """Sets the width to which the lines of the :class:`Pango.Layout` should wrap or
        ellipsized.

        The default value is -1: no width set.

        :param width:
            the desired width in Pango units, or -1 to indicate that no
            wrapping or ellipsization should be performed.
        """
    def set_wrap(self, wrap: WrapMode) -> None:
        """Sets the wrap mode.

        The wrap mode only has effect if a width is set on the layout
        with :meth:`Pango.Layout.set_width`. To turn off wrapping,
        set the width to -1.

        The default value is :const:`Pango.WrapMode.WORD`.
        """

class Attribute: ...

class AttrList:
    """A :class:`Pango.AttrList` represents a list of attributes that apply to a section
    of text.

    The attributes in a :class:`Pango.AttrList` are, in general, allowed to overlap in
    an arbitrary fashion. However, if the attributes are manipulated only through
    :meth:`Pango.AttrList.change`, the overlap between properties will meet
    stricter criteria.

    Since the :class:`Pango.AttrList` structure is stored as a linear list, it is not
    suitable for storing attributes for large amounts of text. In general, you
    should not use a single `PangoAttrList` for more than one paragraph of text.
    """

    def __init__(self) -> None:
        """Create a new empty attribute list."""
    def insert(self, attr: Attribute) -> None:
        """Insert the given attribute into the `PangoAttrList`.

        It will be inserted after all other attributes with a
        matching :attr:`Attribute.start_index`.
        """

class FontDescription:
    """A :class:`Pango.FontDescription` describes a font in an implementation-independent
    manner.

    :class:`PangoFontDescription` structures are used both to list what fonts are
    available on the system and also for specifying the characteristics of
    a font to load.
    """

    def __init__(self) -> None:
        """Creates a new font description structure with all fields unset."""
    def get_size(self) -> int:
        """Gets the size field of a font description.

        See :meth:`Pango.FontDescription.set_size`.

        :returns:
            the size field for the font description in points
            or device units. You must call
            :meth:`Pango.FontDescription.get_size_is_absolute` to find out
            which is the case. Returns 0 if the size field has not previously
            been set or it has been set to 0 explicitly.
            Use :meth:`Pango.FontDescription.get_set_fields` to find out
            if the field was explicitly set or not.
        """
    def get_size_is_absolute(self) -> bool: ...
    def set_absolute_size(self, size: float) -> None: ...
    def set_family(self, family: str) -> None:
        """Sets the family name field of a font description.

        The family
        name represents a family of related font styles, and will
        resolve to a particular :class:`Pango.FontFamily`. In some uses of
        :class:`Pango.FontDescription`, it is also possible to use a comma
        separated list of family names for this field.
        """
    def set_size(self, size: int) -> None:
        """Sets the size field of a font description in fractional points.

        This is mutually exclusive with
        :meth:`Pango.FontDescription.set_absolute_size`.

        :param size:
            the size of the font in points, scaled by :data:`Pango.SCALE`.
            (That is, a `size` value of 10 * Pango.SCALE is a 10 point font.
            The conversion factor between points and device units depends on
            system configuration and the output device. For screen display, a
            logical DPI of 96 is common, in which case a 10 point font corresponds
            to a 10 * (96 / 72) = 13.3 pixel font.
            Use :meth:`Pango.FontDescription.set_absolute_size` if you need
            a particular size in device units.
        """

class FontMetrics:
    def get_ascent(self) -> int: ...
    def get_descent(self) -> int: ...
    def get_height(self) -> int: ...

class Language: ...

class LayoutIter:
    """A :class:`Pango.LayoutIter` can be used to iterate over the visual extents of a
    :class:`Pango.Layout`.
    """

    def get_line_extents(self) -> Tuple[Rectangle, Rectangle]:
        """Obtains the extents of the current line.

        Extents are in layout coordinates (origin is the top-left corner of the entire
        :class:`Pango.Layout`). Thus the extents returned by this function will be the
        same width/height but not at the same x/y as the extents returned from
        :method:`Pango.LayoutLine.get_extents`.
        """
    def get_line_readonly(self) -> LayoutLine:
        """Gets the current line for read-only access.

        This is a faster alternative to :method:`Pango.LayoutIter.get_line`, but the
        user is not expected to modify the contents of the line (glyphs, glyph widths,
        etc.).
        """
    def next_line(self) -> bool:
        """Moves `self` forward to the start of the next line.

        If `self` is already on the last line, returns False.

        :returns:
            whether motion was possible.
        """

class LayoutLine:
    resolved_dir: Direction

    def get_extents(self) -> Tuple[Rectangle, Rectangle]:
        """Computes the logical and ink extents of a layout line.

        See :meth:`Pango.Font.get_glyph_extents` for details
        about the interpretation of the rectangles.

        :returns:
            A tuple containing `ink_rect` and `logical_rect`
        """
    def get_height(self) -> int: ...

class Rectangle:
    x: int
    y: int
    width: int
    height: int

class Alignment(Enum):
    """:class:`Pango.Alignment` describes how to align the lines of a :class:`Pango.Layout`
    within the available space.

    If the :class:`Pango.Layout` is set to justify using :meth:`Pango.Layout.set_justify`,
    this only affects partial lines.

    See :meth:`Pango.Layout.set_auto_dir` for how text direction affects
    the interpretation of :class:`Pango.Alignment` values.
    """

    LEFT: int
    """Put all available space on the right"""
    CENTER: int
    """Center the line within the available space"""
    RIGHT: int
    """Put all available space on the left"""

class Direction(Enum):
    """PangoDirection represents a direction in the Unicode bidirectional algorithm."""

    LTR: int
    """A strong left-to-right direction."""
    RTL: int
    """A strong right-to-left direction."""
    TTB_LTR: int
    """Deprecated value; treated the same as `RTL`."""
    TTB_RTL: int
    """Deprecated value; treated the same as `LTR`."""
    WEAK_LTR: int
    """A weak left-to-right direction."""
    WEAK_RTL: int
    """A weak right-to-left direction."""
    NEUTRAL: int
    """No direction specified."""

class EllipsizeMode(Enum):
    NONE: int
    START: int
    MIDDLE: int
    END: int

class WrapMode(Enum):
    """:class:`Pango.WrapMode` describes how to wrap the lines of a :class:`Pango.Layout`
    to the desired width.

    For :const:`Pango.WrapMode.WORD`, Pango uses break opportunities that are determined
    by the Unicode line breaking algorithm. For :const:`Pango.WrapMode.CHAR`, Pango allows
    breaking at grapheme boundaries that are determined by the Unicode text
    segmentation algorithm.
    """

    WORD: int
    """wrap lines at word boundaries."""
    CHAR: int
    """wrap lines at character boundaries."""
    WORD_CHAR: int
    """wrap lines at word boundaries, but fall back to
    character boundaries if there is not enough space for a full word.
    """

def attr_insert_hyphens_new(insert_hyphens: bool) -> Attribute:
    """Create a new insert-hyphens attribute.

    Pango will insert hyphens when breaking lines in
    the middle of a word. This attribute can be used
    to suppress the hyphen.

    Since: 1.44
    """

def attr_letter_spacing_new(letter_spacing: int) -> Attribute:
    """Create a new letter-spacing attribute.

    Since: 1.6

    :param letter_spacing:
        amount of extra space to add between
        graphemes of the text, in Pango units
    """
