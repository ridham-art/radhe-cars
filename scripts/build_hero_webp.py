"""
One-off: download LCP hero source (Unsplash) and write responsive WebPs under static/images/hero/.
Re-run if you change the source photo. Requires: pip install Pillow requests
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

# Same photo as templates (Find Your Dream Car); fetch large then resize locally.
SOURCE_URL = (
    "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b"
    "?auto=format&fm=jpg&fit=crop&w=2400&q=85"
)
WIDTHS = (640, 768, 960, 1280, 1920)
TARGET_RATIO = 16 / 9
WEBP_QUALITY = 82


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "static" / "images" / "hero"
    out_dir.mkdir(parents=True, exist_ok=True)

    r = requests.get(SOURCE_URL, timeout=120)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content)).convert("RGB")

    w, h = img.size
    if w / h > TARGET_RATIO:
        new_w = int(round(h * TARGET_RATIO))
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(round(w / TARGET_RATIO))
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    for width in WIDTHS:
        height = int(round(width / TARGET_RATIO))
        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        out_path = out_dir / f"dream-car-{width}.webp"
        resized.save(
            out_path,
            "WEBP",
            quality=WEBP_QUALITY,
            method=6,
        )
        print(f"Wrote {out_path.relative_to(root)} ({out_path.stat().st_size // 1024} KB)")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
