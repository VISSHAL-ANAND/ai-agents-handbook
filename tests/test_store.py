from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ledgerlite import store
from ledgerlite.models import Entry

FIXTURES = Path(__file__).parent.parent / "fixtures"


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
    with pytest.raises(ValueError):
        store.load(p)


def test_migrate_v1_adds_currency(tmp_path):
    """Loading a v1 fixture must give every entry currency='INR' and write schema_version=2."""
    import json

    entries = store.load(FIXTURES / "ledger_v1.json")
    assert len(entries) == 2
    assert all(e.currency == "INR" for e in entries)

    out = tmp_path / "migrated.json"
    store.save(out, entries)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    assert all(e["currency"] == "INR" for e in data["entries"])
