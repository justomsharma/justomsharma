"""Pure text layout for the card: grid constants and line builders.

A line is a list of (text, css_class) segments. Everything here works in
character cells. The font is monospace and embedded, so cells map exactly
to pixels.
"""

from __future__ import annotations

from datetime import date

FONT_SIZE = 14
CELL_W = FONT_SIZE * 0.6  # Geist Mono advance = 600/1000 em
CELL_H = 18  # line height

TEXT_COLS = 62
TEXT_ROWS = 38
GAP_COLS = 3

# The portrait uses a smaller face so it can carry real detail; its box is
# exactly as tall as the text column.
ASCII_FONT_SIZE = 8
ASCII_CELL_W = ASCII_FONT_SIZE * 0.6
ASCII_CELL_H = 9
ASCII_COLS = 84
ASCII_ROWS = TEXT_ROWS * CELL_H // ASCII_CELL_H  # 76

Segment = tuple[str, str]
Line = list[Segment]

MIN_DOTS = 2


def leader(key: str, value: str, width: int = TEXT_COLS) -> Line:
    """`key .......... value`, exactly `width` cells wide, value right-aligned."""
    dots = width - len(key) - len(value) - 2
    if dots < MIN_DOTS:
        raise ValueError(f"line too long for {width} cols: {key!r} {value!r}")
    return [(key, "k"), (" " + "." * dots + " ", "d"), (value, "v")]


def leader_rich(key: str, value: Line, width: int = TEXT_COLS) -> Line:
    """Like `leader`, but the value is pre-styled segments."""
    dots = width - len(key) - line_len(value) - 2
    if dots < MIN_DOTS:
        raise ValueError(f"line too long for {width} cols: {key!r}")
    return [(key, "k"), (" " + "." * dots + " ", "d")] + value


def pair(left: tuple[str, str], right: tuple[str, str], width: int = TEXT_COLS) -> Line:
    """Two leader cells side by side: `k .. v | k .. v`."""
    sep = " | "
    lw = (width - len(sep)) // 2
    rw = width - len(sep) - lw
    return leader(*left, width=lw) + [(sep, "d")] + leader(*right, width=rw)


def rule(title: str, width: int = TEXT_COLS, cls: str = "h") -> Line:
    """`title ────────`, filling the line. Section titles get a leading `─ `."""
    fill = width - len(title) - 1
    if fill < 1:
        raise ValueError(f"title too long: {title!r}")
    return [(title, cls), (" " + "─" * fill, "r")]


def section(title: str, width: int = TEXT_COLS) -> Line:
    return [("─ ", "r")] + rule(title, width - 2, cls="s")


def blank() -> Line:
    return []


def line_len(line: Line) -> int:
    return sum(len(t) for t, _ in line)


def fmt_int(n: int) -> str:
    return f"{n:,}"


def _plural(n: int, unit: str) -> str:
    return f"{n} {unit}{'' if n == 1 else 's'}"


def _add_months(d: date, n: int) -> date:
    """`d` plus `n` calendar months, clamping the day (Jan 31 + 1 -> Feb 28)."""
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    next_first = date(year + (month == 12), month % 12 + 1, 1)
    last_day = (next_first - date(year, month, 1)).days
    return date(year, month, min(d.day, last_day))


def uptime(start: date, today: date) -> str:
    """Calendar difference as `2 years, 9 months, 8 days`."""
    if today < start:
        raise ValueError("today is before start")
    total = (today.year - start.year) * 12 + today.month - start.month
    if _add_months(start, total) > today:
        total -= 1
    days = (today - _add_months(start, total)).days
    years, months = divmod(total, 12)
    return ", ".join([_plural(years, "year"), _plural(months, "month"), _plural(days, "day")])
