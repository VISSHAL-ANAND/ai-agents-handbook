"""CSV import parser for ledgerlite.

Parses and validates a CSV file with columns day, category, amount (any order).
Returns (entries, errors). Does not interact with the store.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Entry


def parse_csv(path: Path) -> tuple[list[Entry], list[str]]:
    """Parse and validate a CSV file.

    Returns:
        (entries, errors) — entries is populated only when errors is empty.
        If the file is missing, raises FileNotFoundError.
        If the file has no data rows, raises ValueError.
    """
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")

    entries: list[Entry] = []
    errors: list[str] = []

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"no data rows in {path}")

    for i, row in enumerate(rows, start=1):
        row_errors = _validate_row(row, i)
        if row_errors:
            errors.extend(row_errors)
        else:
            entries.append(_row_to_entry(row))

    # Return empty entries list if there were any errors (no partial import)
    if errors:
        return [], errors
    return entries, []


def _validate_row(row: dict, row_num: int) -> list[str]:
    """Validate a single CSV row. Returns list of error strings (empty if valid)."""
    errs: list[str] = []

    # Validate day
    day_val = row.get("day", "").strip()
    if not day_val:
        errs.append(f"row {row_num}: day is required")
    else:
        try:
            date.fromisoformat(day_val)
        except ValueError:
            errs.append(f"row {row_num}: day '{day_val}' is not a valid ISO date (YYYY-MM-DD)")

    # Validate category
    cat_val = row.get("category", "").strip()
    if not cat_val:
        errs.append(f"row {row_num}: category is required")

    # Validate amount
    amt_val = row.get("amount", "").strip()
    if not amt_val:
        errs.append(f"row {row_num}: amount is required")
    else:
        try:
            value = Decimal(amt_val)
            if not value.is_finite() or value <= 0:
                errs.append(f"row {row_num}: amount must be a positive number (got '{amt_val}')")
        except InvalidOperation:
            errs.append(f"row {row_num}: amount '{amt_val}' is not a valid number")

    return errs


def _row_to_entry(row: dict) -> Entry:
    """Convert a validated row dict to an Entry. Assumes the row has already been validated."""
    return Entry(
        day=date.fromisoformat(row["day"].strip()),
        category=row["category"].strip(),
        amount=Decimal(row["amount"].strip()),
    )
