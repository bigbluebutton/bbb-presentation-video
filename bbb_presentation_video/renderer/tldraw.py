import cairo

from bbb_presentation_video.events import tldraw


class TldrawRenderer:
    """Render tldraw whiteboard shapes"""

    ctx: cairo.Context
    """The cairo rendering context for drawing the whiteboard"""

    def __init__(self, ctx: cairo.Context):
        self.ctx = ctx

    def update_shape(self, event: tldraw.AddShapeEvent) -> None:
        ...
