import struct
from pathlib import Path

import cairo

from bbb_presentation_video.events.helpers import Size
from bbb_presentation_video.renderer.tldraw.shape import ImageShape
from bbb_presentation_video.renderer.tldraw.v2.shape.image import (
    MAX_IMAGE_PIXELS,
    finalize_image,
    load_pixbuf,
    upload_filename,
)


def test_upload_filename_accepts_supported_types() -> None:
    for extension in ["png", "PNG", "jpg", "jpeg", "gif"]:
        src = f"/bigbluebutton/fileUpload/meeting-id/44c71706.{extension}"
        assert upload_filename(src) == f"44c71706.{extension}"


def test_upload_filename_rejects_unsupported_types() -> None:
    assert upload_filename("/bigbluebutton/fileUpload/meeting-id/44c71706.svg") is None
    assert upload_filename("/bigbluebutton/fileUpload/meeting-id/44c71706") is None
    assert upload_filename("") is None


def test_upload_filename_rejects_webp() -> None:
    """There is no webp loader to decode it with, so it is not accepted."""
    assert upload_filename("/bigbluebutton/fileUpload/meeting-id/44c71706.webp") is None


def test_upload_filename_strips_directories() -> None:
    """A source can only ever name a file directly inside the file-uploads directory."""
    assert upload_filename("../../../etc/shadow.png") == "shadow.png"
    assert upload_filename("/etc/ssl/private/server.png") == "server.png"
    assert upload_filename("../../../etc/shadow") is None


def test_load_pixbuf_without_file_uploads_directory(tmp_path: Path) -> None:
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
    file_uploads = directory / "file-uploads"
    file_uploads.mkdir()
    cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1).write_to_png(
        str(file_uploads / "44c71706.png")
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


def test_finalize_image_draws_for_every_shape_sharing_the_image(tmp_path: Path) -> None:
    """A shared decoded image has to draw for the second shape as much as the first."""
    file_uploads = tmp_path / "file-uploads"
    file_uploads.mkdir()
    upload = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
    painter = cairo.Context(upload)
    painter.set_source_rgb(1, 0, 0)
    painter.paint()
    upload.write_to_png(str(file_uploads / "44c71706.png"))

    for _ in range(2):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)
        finalize_image(
            cairo.Context(surface),
            "shape:test",
            image_shape(Size(10, 10)),
            str(tmp_path),
        )
        surface.flush()

        # Away from the edges, where scaling a two pixel image blends towards
        # transparent. Cairo keeps ARGB32 as native byte order, premultiplied.
        centre = 5 * surface.get_stride() + 5 * 4
        (pixel,) = struct.unpack_from("=I", bytes(surface.get_data()), centre)
        assert pixel == 0xFFFF0000, "expected opaque red"


def test_shapes_sharing_a_file_share_one_decoded_image(tmp_path: Path) -> None:
    """Pasting the same upload many times must not decode it many times."""
    write_upload(tmp_path)

    first = load_pixbuf(image_shape(Size(4, 3)), str(tmp_path))
    second = load_pixbuf(image_shape(Size(9, 9)), str(tmp_path))

    assert first is not None
    assert first is second


def test_load_pixbuf_with_excessive_dimensions(tmp_path: Path) -> None:
    """A file small enough to archive can still decode to gigabytes."""
    file_uploads = tmp_path / "file-uploads"
    file_uploads.mkdir()
    # Written rather than committed, since the repository keeps no binary
    # fixtures. Just over the limit, so a missing check would decode it.
    side = 4097
    assert side * side > MAX_IMAGE_PIXELS
    cairo.ImageSurface(cairo.FORMAT_ARGB32, side, side).write_to_png(
        str(file_uploads / "44c71706.png")
    )

    shape = image_shape(Size(4, 3))

    assert load_pixbuf(shape, str(tmp_path)) is None
    assert shape.pixbuf is None
