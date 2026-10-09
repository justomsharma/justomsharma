"""One-off asset prep (run locally, results are committed).

    python -m generator.make_assets

1. Scans portrait.webp into a brightness grid -> portrait.txt
   One char per cell: ' ' = transparent background, '0'..'9' = brightness
   (0 darkest). The daily build maps this to glyphs per theme, so it needs
   no image library.
2. Subsets Geist Mono (same face as omsharma.dev) to the glyphs the card
   uses -> fonts/*.subset.woff2, embedded into the SVG at build time.

Needs: pip install pillow fonttools brotli
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

from generator.layout import ASCII_CELL_H, ASCII_CELL_W, ASCII_COLS, ASCII_ROWS

HERE = Path(__file__).parent

# Crop of the 560x578 cut-out that keeps the head and shoulders but drops
# the empty margin left of the hair.
CROP = (140, 0, 510, 578)

# Glyphs the card can ever render: printable ASCII + the few specials used
# in the copy and rules.
FONT_TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + "─→·…│—"


# Face region inside the crop (eyebrows to chin), and how much more it
# counts than the rest of the subject when building the tone curve.
FACE = (65, 120, 320, 430)
FACE_WEIGHT = 4


def _equalize(lum: Image.Image, alpha: Image.Image) -> Image.Image:
    """Histogram-equalize over the subject, weighted toward the face.

    The cut-out is mostly dark hair and a bright shirt, so a plain stretch
    squeezes the face into three or four levels and the features vanish.
    Counting face pixels FACE_WEIGHT times spreads the face across the
    ramp while hair and shirt keep some gradation.
    """
    mask = alpha.point(lambda a: 255 if a >= 140 else 0)
    hist = lum.histogram(mask=mask)
    face = lum.crop(FACE).histogram(mask=mask.crop(FACE))
    hist = [h + FACE_WEIGHT * f for h, f in zip(hist, face)]
    total = sum(hist) or 1
    lut, acc = [], 0
    for count in hist:
        acc += count
        lut.append(round(255 * acc / total))
    return lum.point(lut)


def scan_portrait() -> list[str]:
    img = Image.open(HERE / "portrait.webp").convert("RGBA").crop(CROP)
    # Fit the crop into the ASCII box (in pixels), keeping aspect.
    box_w, box_h = ASCII_COLS * ASCII_CELL_W, ASCII_ROWS * ASCII_CELL_H
    scale = min(box_w / img.width, box_h / img.height)
    w, h = img.width * scale, img.height * scale
    cols, rows = round(w / ASCII_CELL_W), round(h / ASCII_CELL_H)

    alpha = img.getchannel("A")
    # Sharpen before downsampling so glasses, brows and beard edges survive.
    lum = img.convert("L").filter(ImageFilter.UnsharpMask(radius=3, percent=160, threshold=2))
    lum = _equalize(lum, alpha)
    # Each cell = area average of its pixels.
    small_lum = lum.resize((cols, rows), Image.Resampling.BOX)
    small_alpha = alpha.resize((cols, rows), Image.Resampling.BOX)

    lines = []
    for y in range(rows):
        row = []
        for x in range(cols):
            if small_alpha.getpixel((x, y)) < 140:
                row.append(" ")
            else:
                row.append(str(min(9, small_lum.getpixel((x, y)) * 10 // 256)))
        lines.append("".join(row).rstrip())
    # Pad rows at the top so the portrait sits on the card's baseline.
    return [""] * (ASCII_ROWS - rows) + lines


def subset_fonts() -> None:
    from fontTools import subset

    for weight in ("Regular", "SemiBold"):
        src = HERE / "fonts" / f"GeistMono-{weight}.woff2"
        out = HERE / "fonts" / f"GeistMono-{weight}.subset.woff2"
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = []  # no ligatures: keep a strict 1-char grid
        opts.name_IDs = []
        opts.notdef_outline = True
        font = subset.load_font(str(src), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text=FONT_TEXT)
        sub.subset(font)
        subset.save_font(font, str(out), opts)
        print(f"{out.name}: {out.stat().st_size} bytes")


if __name__ == "__main__":
    grid = scan_portrait()
    (HERE / "portrait.txt").write_text("\n".join(grid) + "\n", encoding="utf-8")
    print(f"portrait.txt: {len(grid)} rows, {max(map(len, grid))} cols max")
    subset_fonts()
