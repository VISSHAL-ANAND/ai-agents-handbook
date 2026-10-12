from datetime import date
from decimal import Decimal

from ledgerlite import report
from ledgerlite.models import Entry


def _e(d, c, a):
    return Entry(date.fromisoformat(d), c, Decimal(a))


def test_month_range_mid_year():
    assert report.month_range(2026, 4) == (date(2026, 4, 1), date(2026, 4, 30))


def test_entries_in_month_includes_both_ends():
    entries = [
        _e("2026-04-01", "a", "1"),
        _e("2026-04-30", "a", "2"),
        _e("2026-05-01", "a", "4"),
    ]
    got = [e.amount for e in report.entries_in_month(entries, 2026, 4)]
    assert got == [Decimal("1"), Decimal("2")]


def test_totals_by_category_sorted():
    entries = [
        _e("2026-04-02", "food", "10"),
        _e("2026-04-03", "auto", "5"),
        _e("2026-04-04", "food", "2.5"),
    ]
    assert report.totals_by_category(entries) == {"auto": Decimal("5"), "food": Decimal("12.5")}


def test_format_report_has_total_line():
    out = report.format_report(2026, 4, {"food": Decimal("12.50")})
    assert out.splitlines()[0] == "Report 2026-04"
    assert out.splitlines()[-1].split() == ["TOTAL", "12.50"]


# Regression test for issue #131 — report crashes for December
def test_month_range_december():
    """month_range must not raise for month=12 (issue #131)."""
    first, last = report.month_range(2026, 12)
    assert first == date(2026, 12, 1)
    assert last == date(2026, 12, 31)


# Characterization tests: month_range across all 12 months of 2024 (a leap year)
# Pins the exact first and last day returned for every month so regressions are caught.
def test_month_range_2024_jan():
    assert report.month_range(2024, 1) == (date(2024, 1, 1), date(2024, 1, 31))


def test_month_range_2024_feb_leap():
    # 2024 is a leap year — February has 29 days
    assert report.month_range(2024, 2) == (date(2024, 2, 1), date(2024, 2, 29))


def test_month_range_2024_mar():
    assert report.month_range(2024, 3) == (date(2024, 3, 1), date(2024, 3, 31))


def test_month_range_2024_apr():
    assert report.month_range(2024, 4) == (date(2024, 4, 1), date(2024, 4, 30))


def test_month_range_2024_may():
    assert report.month_range(2024, 5) == (date(2024, 5, 1), date(2024, 5, 31))


def test_month_range_2024_jun():
    assert report.month_range(2024, 6) == (date(2024, 6, 1), date(2024, 6, 30))


def test_month_range_2024_jul():
    assert report.month_range(2024, 7) == (date(2024, 7, 1), date(2024, 7, 31))


def test_month_range_2024_aug():
    assert report.month_range(2024, 8) == (date(2024, 8, 1), date(2024, 8, 31))


def test_month_range_2024_sep():
    assert report.month_range(2024, 9) == (date(2024, 9, 1), date(2024, 9, 30))


def test_month_range_2024_oct():
    assert report.month_range(2024, 10) == (date(2024, 10, 1), date(2024, 10, 31))


def test_month_range_2024_nov():
    assert report.month_range(2024, 11) == (date(2024, 11, 1), date(2024, 11, 30))


def test_month_range_2024_dec():
    # Also exercises the December fix (issue #131)
    assert report.month_range(2024, 12) == (date(2024, 12, 1), date(2024, 12, 31))
