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
    assert data["schema_version"] == 3
    assert all(e["currency"] == "INR" for e in data["entries"])

def test_migrate_v1_adds_budgets(tmp_path):
    """v1 fixture loads without error, entries preserved, budgets empty; save writes v2."""
    import json

    entries = store.load(FIXTURES / "ledger_v1.json")
    assert len(entries) == 2
    budgets = store.load_budgets(FIXTURES / "ledger_v1.json")
    assert budgets == {}

    out = tmp_path / "out.json"
    store.save(out, entries)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["budgets"] == {}

def test_budgets_round_trip(tmp_path):
    """save_budgets then load_budgets returns identical Decimal values."""
    p = tmp_path / "ledger.json"
    budgets = {"food": Decimal("5000"), "rent": Decimal("15000.50")}
    store.save_budgets(p, budgets)
    loaded = store.load_budgets(p)
    assert loaded == budgets
    # Confirm no float conversion: values are Decimal
    for v in loaded.values():
        assert isinstance(v, Decimal)

def test_save_preserves_budgets(tmp_path):
    """store.save(entries) must not discard budgets already on disk."""
    import json

    p = tmp_path / "ledger.json"
    entries = [Entry(date(2026, 1, 5), "rent", Decimal("15000"))]
    budgets = {"food": Decimal("5000")}

    store.save_budgets(p, budgets)
    store.save(p, entries)  # must preserve budgets

    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["budgets"] == {"food": "5000"}
    assert len(data["entries"]) == 1

def test_save_budgets_preserves_entries(tmp_path):
    """save_budgets() must not discard entries already on disk."""
    p = tmp_path / "ledger.json"
    entries = [Entry(date(2026, 1, 5), "rent", Decimal("15000"))]
    budgets = {"food": Decimal("5000")}

    store.save(p, entries)
    store.save_budgets(p, budgets)  # must preserve entries

    reloaded = store.load(p)
    assert len(reloaded) == 1
    assert reloaded[0].category == "rent"

def test_save_corrupt_ledger_raises(tmp_path):
    """store.save() on a corrupt existing file must raise, not overwrite with lost budgets."""
    import json as json_mod

    p = tmp_path / "ledger.json"
    p.write_text("{not json", encoding="utf-8")
    original_content = p.read_text(encoding="utf-8")

    entries = [Entry(date(2026, 1, 5), "rent", Decimal("15000"))]
    with pytest.raises((ValueError, json_mod.JSONDecodeError)):
        store.save(p, entries)

    # Original corrupt file must not be overwritten
    assert p.read_text(encoding="utf-8") == original_content
