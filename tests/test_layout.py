from datetime import date

import pytest

from generator.layout import TEXT_COLS, fmt_int, leader, line_len, pair, rule, section, uptime


def test_leader_is_exact_width_and_right_aligned():
    line = leader("Host", "Jobtwine, Bangalore")
    assert line_len(line) == TEXT_COLS
    assert line[0] == ("Host", "k")
    assert line[-1] == ("Jobtwine, Bangalore", "v")
    assert set(line[1][0].strip()) == {"."}


def test_leader_rejects_overflow():
    with pytest.raises(ValueError):
        leader("Key", "x" * TEXT_COLS)


def test_leader_keeps_minimum_dots():
    value = "v" * (TEXT_COLS - len("Key") - 4)
    assert line_len(leader("Key", value)) == TEXT_COLS
    with pytest.raises(ValueError):
        leader("Key", value + "v")


def test_pair_is_exact_width():
    line = pair(("Repos", "6 {Contributed: 1}"), ("Commits", "1,204"))
    assert line_len(line) == TEXT_COLS
    assert ("Commits", "k") in line


def test_rules_fill_the_line():
    assert line_len(rule("om@sharma")) == TEXT_COLS
    assert line_len(section("Contact")) == TEXT_COLS


@pytest.mark.parametrize(
    "start,today,expected",
    [
        (date(2024, 1, 1), date(2026, 10, 9), "2 years, 9 months, 8 days"),
        (date(2024, 1, 1), date(2025, 2, 2), "1 year, 1 month, 1 day"),
        (date(2024, 1, 1), date(2024, 1, 1), "0 years, 0 months, 0 days"),
        (date(2024, 1, 31), date(2024, 3, 1), "0 years, 1 month, 1 day"),
        (date(2024, 2, 29), date(2025, 2, 28), "1 year, 0 months, 0 days"),
        (date(2024, 1, 15), date(2024, 12, 14), "0 years, 10 months, 29 days"),
    ],
)
def test_uptime(start, today, expected):
    assert uptime(start, today) == expected


def test_uptime_rejects_future_start():
    with pytest.raises(ValueError):
        uptime(date(2030, 1, 1), date(2026, 1, 1))


def test_fmt_int():
    assert fmt_int(48201) == "48,201"
    assert fmt_int(0) == "0"
