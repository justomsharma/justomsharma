"""Turns card lines + the portrait grid into a self-contained SVG.

Self-contained matters: GitHub serves README images through a proxy that
blocks external fetches, so the font is embedded as a data URI and all
styling is inline. Animation is plain CSS, which GitHub's <img> renders.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from generator.layout import (
    ASCII_CELL_H,
    ASCII_CELL_W,
    ASCII_COLS,
    ASCII_FONT_SIZE,
    ASCII_ROWS,
    CELL_H,
    CELL_W,
    FONT_SIZE,
    GAP_COLS,
    TEXT_COLS,
    TEXT_ROWS,
    Line,
)

FONTS = Path(__file__).parent / "fonts"
GLYPH = "@"
PAD = 26
BASELINE = 13  # px from a cell's top to the text baseline at 14px
ASCII_BASELINE = 7

def opacity(density: int, theme: "Theme") -> float:
    """Portrait opacity for density 1..9; linear (gamma 1) maps tone straight to ink."""
    return round(0.06 + 0.94 * (density / 9) ** theme.tone_gamma, 2)

# Reveal timing: the whole card streams in well under the 2s it brags about.
ASCII_STEP_MS = 11
TEXT_START_MS = 180
TEXT_STEP_MS = 38


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    border: str
    ink: str
    accent: str
    faint: str
    rule: str
    add: str
    rem: str
    # Dark: light builds the face on black (bright pixel = dense glyph).
    # Light: ink builds it on paper (dark pixel = dense glyph).
    ink_on_paper: bool
    # Portrait opacity curve exponent: >1 thins midtones. On paper that keeps
    # skin light so eyes, brows and beard carry the face instead of the hair.
    tone_gamma: float = 1.0


DARK = Theme(
    name="dark",
    bg="#050505",
    border="rgba(232,226,213,.09)",
    ink="#e8e2d5",
    accent="#ff6b47",
    faint="rgba(232,226,213,.26)",
    rule="rgba(232,226,213,.16)",
    add="#8cc084",
    rem="#e5737a",
    ink_on_paper=False,
)

LIGHT = Theme(
    name="light",
    bg="#f7f4ec",
    border="rgba(34,28,20,.12)",
    ink="#221c14",
    accent="#d8502b",
    faint="rgba(34,28,20,.34)",
    rule="rgba(34,28,20,.2)",
    add="#3c7a3a",
    rem="#b8323a",
    ink_on_paper=True,
    tone_gamma=1.5,
)

TEXT_X = PAD + ASCII_COLS * ASCII_CELL_W + GAP_COLS * CELL_W
WIDTH = round(TEXT_X + TEXT_COLS * CELL_W + PAD)


def _font_face(weight: int, file: str) -> str:
    data = base64.b64encode((FONTS / file).read_bytes()).decode()
    return (
        "@font-face{font-family:'Geist Mono Card';font-weight:%d;"
        "src:url(data:font/woff2;base64,%s) format('woff2')}" % (weight, data)
    )


def glyph(level: int, theme: Theme) -> tuple[str, str]:
    """(char, css class) for a portrait cell of brightness `level` 0..9.

    Tone rides on opacity (class l1..l9) over one dense glyph. A classic
    ' .:-=+*#%@' ramp looked more "ASCII" but its thin midtone glyphs
    erased the glasses and beard at this size; a uniform glyph keeps the
    face recognizable.
    """
    density = 9 - level if theme.ink_on_paper else level
    if density == 0:
        return " ", ""
    return GLYPH, f"l{density}"


def portrait_lines(grid: list[str], theme: Theme) -> list[Line]:
    out: list[Line] = []
    for row in grid:
        line: Line = []
        for cell in row:
            char, cls = (" ", "") if cell == " " else glyph(int(cell), theme)
            if line and line[-1][1] == cls:
                line[-1] = (line[-1][0] + char, cls)
            else:
                line.append((char, cls))
        out.append(line)
    return out


def _text(line: Line, x: float, y: float, delay_ms: int, cls: str = "ln") -> str:
    parts = []
    for text, seg_cls in line:
        if not text:
            continue
        t = escape(text)
        parts.append(f'<tspan class="{seg_cls}">{t}</tspan>' if seg_cls else t)
    return (
        f'<text class="{cls}" x="{x:.1f}" y="{y:g}" style="animation-delay:{delay_ms}ms">'
        + "".join(parts)
        + "</text>"
    )


def render(lines: list[Line], grid: list[str], theme: Theme, title: str, desc: str) -> str:
    if len(lines) > TEXT_ROWS:
        raise ValueError(f"{len(lines)} lines, card holds {TEXT_ROWS}")
    height = PAD * 2 + TEXT_ROWS * CELL_H
    tx = TEXT_X
    t = theme

    css = "".join(
        [
            _font_face(400, "GeistMono-Regular.subset.woff2"),
            _font_face(600, "GeistMono-SemiBold.subset.woff2"),
            "text{font-family:'Geist Mono Card',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
            f"font-size:{FONT_SIZE}px;white-space:pre;fill:{t.ink}}}",
            f".k{{fill:{t.accent}}}.v{{fill:{t.ink}}}.d{{fill:{t.faint}}}.r{{fill:{t.rule}}}",
            f".h{{fill:{t.ink};font-weight:600}}.s{{fill:{t.ink};font-weight:600}}",
            f".add{{fill:{t.add}}}.del{{fill:{t.rem}}}",
            f".pa{{font-size:{ASCII_FONT_SIZE}px}}",
            "".join(f".l{d}{{opacity:{opacity(d, t)}}}" for d in range(1, 10)),
            ".ln,.pa{animation:in .34s ease-out both}",
            "@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}",
            ".cur{animation:blink 1.1s steps(1) infinite}",
            "@keyframes blink{50%{opacity:0}}",
            "@media (prefers-reduced-motion:reduce){.ln,.pa,.cur{animation:none}}",
        ]
    )

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="t d">',
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>',
        f"<style>{css}</style>",
        "<defs>"
        '<linearGradient id="fadeg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".64" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
        f'<mask id="fade" maskUnits="userSpaceOnUse"><rect x="0" y="0" width="{WIDTH}" height="{height}" fill="url(#fadeg)"/></mask>'
        "</defs>",
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="12" fill="{t.bg}" stroke="{t.border}"/>',
        '<g mask="url(#fade)">',
    ]
    for i, line in enumerate(portrait_lines(grid, theme)):
        y = PAD + i * ASCII_CELL_H + ASCII_BASELINE
        out.append(_text(line, PAD, y, i * ASCII_STEP_MS, cls="pa"))
    out.append("</g>")

    cursor = None
    for j, line in enumerate(lines):
        y = PAD + j * CELL_H + BASELINE
        delay = TEXT_START_MS + j * TEXT_STEP_MS
        out.append(_text(line, tx, y, delay))
        if any(cls == "cursor" for _, cls in line):
            col = sum(len(s) for s, c in line if c != "cursor")
            cursor = (tx + col * CELL_W, PAD + j * CELL_H + 2, delay)
    if cursor:
        x, y, delay = cursor
        out.append(
            f'<g class="ln" style="animation-delay:{delay}ms"><rect class="cur" x="{x:.1f}" y="{y}" '
            f'width="{CELL_W:.1f}" height="{CELL_H - 3}" fill="{t.accent}"/></g>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"
