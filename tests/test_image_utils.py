from io import BytesIO

from PIL import Image

from app.image_utils import make_thumbnail


def _sample_png_bytes() -> bytes:
    img = Image.new("RGB", (400, 300), color=(200, 50, 50))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_make_thumbnail_shrinks_image():
    thumb_bytes = make_thumbnail(_sample_png_bytes())
    with Image.open(BytesIO(thumb_bytes)) as thumb:
        assert thumb.width <= 128
        assert thumb.height <= 128
