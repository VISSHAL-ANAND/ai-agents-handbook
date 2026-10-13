"""Tests for the CSV import parser. Written before implementation (TDD)."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ledgerlite.importer import parse_csv
from ledgerlite.models import Entry


def _write_csv(tmp_path: Path, rows: list[dict], fieldnames=None) -> Path:
    """Helper: write a CSV file and return its path."""
    p = tmp_path / "test.csv"
    if fieldnames is None:
        fieldnames = ["day", "category", "amount"]
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return p


def test_parse_valid_csv(tmp_path):
    p = _write_csv(tmp_path, [
        {"day": "2024-01-15", "category": "food", "amount": "120.50"},
        {"day": "2024-01-16", "category": "transport", "amount": "45.00"},
    ])
    entries, errors = parse_csv(p)
    assert errors == []
    assert len(entries) == 2
    assert entries[0] == Entry(date(2024, 1, 15), "food", Decimal("120.50"))
    assert entries[1] == Entry(date(2024, 1, 16), "transport", Decimal("45.00"))


def test_parse_invalid_amount(tmp_path):
    p = _write_csv(tmp_path, [{"day": "2024-01-01", "category": "food", "amount": "notanumber"}])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1
    assert "row 1" in errors[0]
    assert "amount" in errors[0].lower()


def test_parse_negative_amount(tmp_path):
    p = _write_csv(tmp_path, [{"day": "2024-01-01", "category": "food", "amount": "-10"}])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1
    assert "row 1" in errors[0]


def test_parse_zero_amount(tmp_path):
    p = _write_csv(tmp_path, [{"day": "2024-01-01", "category": "food", "amount": "0"}])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1


def test_parse_empty_category(tmp_path):
    p = _write_csv(tmp_path, [{"day": "2024-01-01", "category": "", "amount": "10.00"}])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1
    assert "row 1" in errors[0]
    assert "category" in errors[0].lower()


def test_parse_invalid_date(tmp_path):
    p = _write_csv(tmp_path, [{"day": "not-a-date", "category": "food", "amount": "10.00"}])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1
    assert "row 1" in errors[0]
    assert "day" in errors[0].lower()


def test_parse_multiple_errors(tmp_path):
    """All errors are collected, not just the first."""
    p = _write_csv(tmp_path, [
        {"day": "bad-date", "category": "food", "amount": "10.00"},
        {"day": "2024-01-02", "category": "", "amount": "20.00"},
        {"day": "2024-01-03", "category": "food", "amount": "-5"},
    ])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 3
    assert any("row 1" in e for e in errors)
    assert any("row 2" in e for e in errors)
    assert any("row 3" in e for e in errors)


def test_parse_column_order_independent(tmp_path):
    """Columns in non-standard order still parse correctly."""
    p = _write_csv(tmp_path, [
        {"amount": "99.99", "day": "2024-06-01", "category": "rent"},
    ], fieldnames=["amount", "day", "category"])
    entries, errors = parse_csv(p)
    assert errors == []
    assert len(entries) == 1
    assert entries[0].amount == Decimal("99.99")
    assert entries[0].category == "rent"


def test_parse_file_not_found(tmp_path):
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_csv(tmp_path / "nonexistent.csv")


def test_parse_empty_file(tmp_path):
    """Empty file (no header) raises ValueError."""
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows"):
        parse_csv(p)


def test_parse_header_only(tmp_path):
    """Header-only file raises ValueError."""
    p = tmp_path / "header.csv"
    p.write_text("day,category,amount\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no data rows"):
        parse_csv(p)


# --- Integration and edge case tests (Task 3) ---

def test_import_preserves_existing_entries(tmp_path):
    """Importing into a ledger with existing entries must not modify those entries."""
    from ledgerlite import store
    from ledgerlite.cli import main as cli_main

    ledger = tmp_path / "l.json"
    # pre-load two entries via CLI
    cli_main(["--ledger", str(ledger), "add", "--day", "2024-01-01",
              "--category", "seed", "--amount", "999"])
    cli_main(["--ledger", str(ledger), "add", "--day", "2024-01-02",
              "--category", "seed2", "--amount", "888"])

    p = _write_csv(tmp_path, [{"day": "2024-06-01", "category": "new", "amount": "1"}])
    cli_main(["--ledger", str(ledger), "import", str(p)])

    entries = store.load(ledger)
    assert len(entries) == 3
    # originals untouched
    assert any(e.category == "seed" for e in entries)
    assert any(e.category == "seed2" for e in entries)


def test_import_decimal_precision(tmp_path):
    """Amounts with many decimal places are stored exactly as Decimal, not float-rounded."""
    p = _write_csv(tmp_path, [{"day": "2024-05-05", "category": "misc", "amount": "1.23456789"}])
    entries, errors = parse_csv(p)
    assert errors == []
    assert str(entries[0].amount) == "1.23456789"


def test_import_mixed_valid_invalid_no_write(tmp_path):
    """A mix of valid and invalid rows writes nothing (atomic reject)."""
    p = _write_csv(tmp_path, [
        {"day": "2024-04-01", "category": "food", "amount": "100"},
        {"day": "2024-04-02", "category": "food", "amount": "bad"},  # invalid
    ])
    entries, errors = parse_csv(p)
    assert entries == []
    assert len(errors) == 1
    assert "row 2" in errors[0]
