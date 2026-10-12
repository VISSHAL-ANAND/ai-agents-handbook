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
