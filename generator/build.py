"""Regenerate the profile card.

    python -m generator.build              # live stats (needs GITHUB_TOKEN), cache fallback
    python -m generator.build --offline    # cached stats only
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from generator.layout import TEXT_COLS, line_len
from generator.profile import LOGIN, card_lines
from generator.render import DARK, LIGHT, render
from generator.stats import get_stats

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "stats.json"
ASSETS = ROOT / "assets"
IST = timezone(timedelta(hours=5, minutes=30))

TITLE = "Om Sharma, AI Engineer"
DESC = (
    "Terminal-style profile card: an ASCII portrait of Om Sharma beside his details. "
    "AI Engineer building real-time voice and LLM systems at Jobtwine, Bangalore. "
    "Sub-2-second p50 voice pipelines. Contact: omsharma.dev, justomsharma@gmail.com."
)


def build(offline: bool = False, today: date | None = None) -> list[Path]:
    today = today or datetime.now(IST).date()
    stats, fresh = get_stats(LOGIN, CACHE, fetch=_no_fetch if offline else None)
    if not fresh and os.environ.get("GITHUB_ACTIONS"):
        print("::warning::Live GitHub stats unavailable; card built from cache/stats.json")
    lines = card_lines(stats, today)
    for line in lines:
        assert line_len(line) <= TEXT_COLS, line
    grid = (Path(__file__).parent / "portrait.txt").read_text(encoding="utf-8").splitlines()

    ASSETS.mkdir(exist_ok=True)
    written = []
    for theme in (DARK, LIGHT):
        path = ASSETS / f"{theme.name}.svg"
        path.write_text(render(lines, grid, theme, TITLE, DESC), encoding="utf-8", newline="\n")
        written.append(path)
    print(f"built {', '.join(p.name for p in written)} for {today} ({'live' if fresh else 'cached'} stats)")
    return written


def _no_fetch(*_):
    raise OSError("offline")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--today", type=date.fromisoformat)
    args = ap.parse_args()
    build(offline=args.offline, today=args.today)
