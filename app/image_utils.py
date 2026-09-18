"""Product-image helpers.

DEMO NOTE (Team Stormbreakers): this file is the "unreachable critical CVE"
scenario. `requirements.txt` pins pillow==8.1.0, which is vulnerable to
CVE-2022-22817 / GHSA-8vj2-vxx3-667w (arbitrary expression evaluation via
PIL.ImageMath.eval, CVSS 9.8 critical, fixed in 9.0.1).

This module imports Pillow and uses it, but only through `Image.open` /
`Image.thumbnail` — it never touches `PIL.ImageMath.eval`. That makes the
CVE "unreachable" even though the vulnerable package IS imported: the
Security Agent's search_imports tool finds the import, but
search_symbol_usage finds no call site for `ImageMath.eval` anywhere in the
repo, so it should classify this as unreachable -> 0 score impact, shown in
the report but not weighted as a blocker (see PRD Q2).
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image

THUMBNAIL_SIZE = (128, 128)


def make_thumbnail(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail(THUMBNAIL_SIZE)
        out = BytesIO()
        img.save(out, format="JPEG")
        return out.getvalue()
