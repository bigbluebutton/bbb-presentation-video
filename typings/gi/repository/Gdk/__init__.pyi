import cairo
from gi.repository import GdkPixbuf

def cairo_set_source_pixbuf(
    cr: cairo.Context, pixbuf: GdkPixbuf.Pixbuf, pixbuf_x: float, pixbuf_y: float
) -> None: ...
