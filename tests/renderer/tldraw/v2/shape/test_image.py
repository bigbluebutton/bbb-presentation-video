from pathlib import Path

import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import ImageShape
from bbb_presentation_video.renderer.tldraw.v2.shape.image import (
    finalize_image,
    load_pixbuf,
    upload_filename,
)


def test_upload_filename_accepts_supported_types() -> None:
    for extension in ["png", "PNG", "jpg", "jpeg", "gif", "webp"]:
        src = f"/bigbluebutton/fileUpload/meeting-id/44c71706.{extension}"
        assert upload_filename(src) == f"44c71706.{extension}"


def test_upload_filename_rejects_unsupported_types() -> None:
    assert upload_filename("/bigbluebutton/fileUpload/meeting-id/44c71706.svg") is None
    assert upload_filename("/bigbluebutton/fileUpload/meeting-id/44c71706") is None
    assert upload_filename("") is None


def test_upload_filename_strips_directories() -> None:
    """A source can only ever name a file directly inside the uploads directory."""
    assert upload_filename("../../../etc/shadow.png") == "shadow.png"
    assert upload_filename("/etc/ssl/private/server.png") == "server.png"
    assert upload_filename("../../../etc/shadow") is None


def test_load_pixbuf_without_uploads_directory(tmp_path: Path) -> None:
    """Recordings made before pasted images were archived still have to render."""
    shape = ImageShape()
    shape.src = "/bigbluebutton/fileUpload/meeting-id/44c71706.png"

    assert load_pixbuf(shape, str(tmp_path)) is None
    assert shape.pixbuf is None

    # The failure is remembered, so re-rendering does not retry the missing file
    assert shape.pixbuf_loaded == True


def test_load_pixbuf_without_source(tmp_path: Path) -> None:
    assert load_pixbuf(ImageShape(), str(tmp_path)) is None


def write_upload(directory: Path) -> None:
    """Put a readable one pixel image where an archived upload would be."""
    uploads = directory / "uploads"
    uploads.mkdir()
    cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1).write_to_png(
        str(uploads / "44c71706.png")
    )


def image_shape(size: Size) -> ImageShape:
    shape = ImageShape()
    shape.src = "/bigbluebutton/fileUpload/meeting-id/44c71706.png"
    shape.size = size
    return shape


def test_finalize_image_with_degenerate_size(tmp_path: Path) -> None:
    """A shape whose size never got set must be skipped, not crash the render."""
    write_upload(tmp_path)
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10))

    finalize_image(ctx, "shape:test", image_shape(Size(0, 0)), str(tmp_path))


def test_finalize_image_with_a_size(tmp_path: Path) -> None:
    write_upload(tmp_path)
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10))
    shape = image_shape(Size(4, 3))

    finalize_image(ctx, "shape:test", shape, str(tmp_path))

    # The image really was readable, so the skip above was the size check
    assert shape.pixbuf is not None
