from datetime import date
from decimal import Decimal

from ledgerlite.models import Entry


def test_roundtrip():
    e = Entry(day=date(2026, 3, 14), category="food", amount=Decimal("120.50"))
    assert Entry.from_dict(e.to_dict()) == e


def test_amount_is_decimal_not_float():
    e = Entry.from_dict({"day": "2026-01-01", "category": "x", "amount": "0.10", "currency": "INR"})
    assert e.amount + Decimal("0.20") == Decimal("0.30")
