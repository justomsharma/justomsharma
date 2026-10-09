import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pytest

from generator.layout import ASCII_COLS, ASCII_ROWS, TEXT_COLS, TEXT_ROWS, line_len
from generator.profile import card_lines
from generator.render import DARK, LIGHT, WIDTH, glyph, portrait_lines, render
from generator.stats import Stats

NS = "{http://www.w3.org/2000/svg}"
GRID = (Path(__file__).parent.parent / "generator" / "portrait.txt").read_text(encoding="utf-8").splitlines()


def stats(**kw):
    base = dict(repos=6, contributed=0, stars=0, followers=0, commits=209,
                contributions_1y=281, additions=98323, deletions=6011)
    return Stats(**{**base, **kw})


def svg(theme=DARK, s=None):
    return render(card_lines(s or stats(), date(2026, 10, 9)), GRID, theme, "T & t", "D < d")


@pytest.mark.parametrize("theme", [DARK, LIGHT])
def test_svg_is_well_formed_and_sized(theme):
    root = ET.fromstring(svg(theme))
    assert root.get("width") == str(WIDTH)
    assert root.find(f"{NS}title").text == "T & t"


@pytest.mark.parametrize("theme", [DARK, LIGHT])
def test_every_row_keeps_its_row_class(theme):
    root = ET.fromstring(svg(theme))
    rows = root.iter(f"{NS}text")
    classes = [t.get("class") for t in rows]
    assert classes.count("pa") == ASCII_ROWS
    assert classes.count("ln") == TEXT_ROWS
    assert set(classes) == {"pa", "ln"}


def test_card_fills_exactly_the_text_rows():
    lines = card_lines(stats(), date(2026, 10, 9))
    assert len(lines) == TEXT_ROWS
    assert all(line_len(l) <= TEXT_COLS for l in lines)


def test_portrait_grid_fits_its_box():
    assert len(GRID) == ASCII_ROWS
    assert max(map(len, GRID)) <= ASCII_COLS
    assert set("".join(GRID)) <= set(" 0123456789")


def test_svg_is_self_contained():
    out = svg()
    # GitHub's image proxy blocks external fetches: only data: URIs allowed.
    urls = re.findall(r"url\(([^)#][^)]*)\)", out)
    assert urls and all(u.startswith("data:") for u in urls)
    assert "http://" not in out.replace("http://www.w3.org/2000/svg", "")
    assert "https://" not in out


def test_svg_stays_small():
    assert len(svg().encode()) < 120_000


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion:reduce" in svg()


def test_text_is_escaped():
    lines = [[("W&B <x>", "v")]]
    out = render(lines, GRID, DARK, "t", "d")
    ET.fromstring(out)
    assert "W&amp;B &lt;x&gt;" in out


def test_glyph_mapping_inverts_between_themes():
    assert glyph(9, DARK) == ("@", "l9")
    assert glyph(9, LIGHT) == (" ", "")
    assert glyph(0, LIGHT) == ("@", "l9")
    assert glyph(0, DARK) == (" ", "")
    assert glyph(3, DARK) == ("@", "l3")


def test_portrait_lines_merge_runs_and_keep_width():
    lines = portrait_lines(["  99 0", ""], DARK)
    assert line_len(lines[0]) == 6
    assert lines[1] == []


def test_stats_social_slot_appears_only_when_meaningful():
    flat = lambda s: "".join(t for l in card_lines(s, date(2026, 10, 9)) for t, _ in l)
    assert "Stars" not in flat(stats(stars=3))
    assert "Stars" in flat(stats(stars=42))
    assert "Followers" in flat(stats(followers=12))
    assert "Contributed" not in flat(stats(contributed=0))
    assert "{Contributed: 2}" in flat(stats(contributed=2))


def test_large_numbers_still_fit():
    big = stats(repos=120, contributed=45, stars=12000, commits=123456,
                contributions_1y=9999, additions=12_345_678, deletions=2_345_678)
    lines = card_lines(big, date(2026, 10, 9))
    assert all(line_len(l) <= TEXT_COLS for l in lines)
