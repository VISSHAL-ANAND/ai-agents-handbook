from datetime import date
from decimal import Decimal

from ledgerlite import store
from ledgerlite.models import Entry


def test_missing_file_is_empty(tmp_path):
    assert store.load(tmp_path / "nope.json") == []


def test_save_then_load(tmp_path):
    p = tmp_path / "ledger.json"
    entries = [
        Entry(date(2026, 1, 5), "rent", Decimal("15000")),
        Entry(date(2026, 1, 6), "food", Decimal("250.25")),
    ]
    store.save(p, entries)
    assert store.load(p) == entries


def test_corrupt_file_raises(tmp_path):
    p = tmp_path / "ledger.json"
    p.write_text("{not json", encoding="utf-8")
    assert store.load(p) == []  # robust loading
