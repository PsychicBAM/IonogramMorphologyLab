"""Generate the branded Ionogram Morphology Lab Windows icon (.ico + .png).

Writes a PNG-compressed multi-size ICO (Windows Vista+), which is more reliable
than Pillow's legacy BMP-ICO writer for multiple sizes.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = (16, 24, 32, 48, 64, 128, 256)


def _draw(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg = (18, 62, 78, 255)
    accent = (232, 168, 74, 255)
    trace = (236, 244, 248, 255)
    axis = (120, 160, 175, 255)
    m = max(1, size // 16)
    d.rectangle([m, m, size - 1 - m, size - 1 - m], fill=bg)
    ax = m + size // 5
    lw = max(1, size // 32)
    d.line([(ax, size - ax), (size - ax, size - ax)], fill=axis, width=lw)
    d.line([(ax, ax), (ax, size - ax)], fill=axis, width=lw)
    pts = [
        (
            ax + int((size - 2 * ax) * (i / 7)),
            size - ax - int((size - 2 * ax) * (0.25 + 0.45 * abs((i - 3.5) / 3.5))),
        )
        for i in range(8)
    ]
    d.line(pts, fill=trace, width=max(1, size // 18))
    if size >= 32:
        mid = pts[4]
        d.ellipse(
            [mid[0] - size // 18, mid[1] - size // 28, mid[0] + size // 10, mid[1] + size // 28],
            outline=accent,
            width=max(1, size // 40),
        )
        d.rectangle(
            [
                size - m - size // 5,
                m + size // 10,
                size - m - size // 5 + max(2, size // 20),
                m + size // 3,
            ],
            fill=accent,
        )
    return im


def _png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def write_png_ico(path: Path, images: list[Image.Image]) -> None:
    """Write ICO with PNG-compressed image entries."""
    count = len(images)
    # ICONDIR + ICONDIRENTRY * count
    offset = 6 + 16 * count
    entries: list[tuple[int, int, bytes]] = []
    blobs: list[bytes] = []
    for im in images:
        data = _png_bytes(im)
        w = 0 if im.width >= 256 else im.width
        h = 0 if im.height >= 256 else im.height
        entries.append((w, h, data))
        blobs.append(data)

    out = bytearray()
    out += struct.pack("<HHH", 0, 1, count)  # reserved, type=icon, count
    cur = offset
    for w, h, data in entries:
        # width, height, colors, reserved, planes, bitcount, bytes, offset
        out += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), cur)
        cur += len(data)
    for data in blobs:
        out += data
    path.write_bytes(bytes(out))


def main() -> Path:
    root = Path(__file__).resolve().parents[1] / "assets"
    root.mkdir(parents=True, exist_ok=True)
    images = [_draw(s) for s in SIZES]
    ico = root / "IonogramMorphologyLab.ico"
    png = root / "IonogramMorphologyLab.png"
    write_png_ico(ico, images)
    images[-1].save(png)
    opened = Image.open(ico)
    entries = sorted(opened.ico.sizes()) if hasattr(opened, "ico") else [opened.size]
    print(f"wrote {ico} ({ico.stat().st_size} bytes) entries={entries}")
    print(f"wrote {png}")
    return ico


if __name__ == "__main__":
    main()
