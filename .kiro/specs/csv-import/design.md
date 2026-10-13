# Design: CSV import

## Architecture

The import feature is implemented as:
- A new `cmd_import` function in `src/ledgerlite/cli.py` (following the existing command pattern)
- A new `importer.py` module in `src/ledgerlite/` that contains the pure parsing and validation logic (testable independently of CLI arg parsing)
- New tests in `tests/test_importer.py`

No changes to `models.py`, `store.py`, or `report.py`. No schema migration needed (no new Entry fields).

## Module: src/ledgerlite/importer.py

```
parse_csv(path: Path) -> tuple[list[Entry], list[str]]
```
- Opens the file, reads with `csv.DictReader`
- For each row, validates day (ISO date), category (non-empty), amount (positive Decimal)
- Returns `(entries, errors)` where `errors` is a list of human-readable strings like `"row 2: amount must be positive"`
- Does NOT interact with the store — pure parsing

## CLI: cmd_import in cli.py

```
def cmd_import(args: argparse.Namespace) -> int:
    # 1. Check file exists
    # 2. Call parse_csv → (entries, errors)
    # 3. If errors: print to stderr, return 2
    # 4. If no entries: print error, return 2
    # 5. Load existing ledger
    # 6. Deduplicate: skip entries already in ledger (warn per duplicate)
    # 7. If no new entries after dedup: still succeed (0) if no errors
    # 8. Append new entries, save, print "imported N entries"
```

## Parser decisions

- `csv.DictReader` handles the header row automatically and allows any column order.
- Validation reuses the same logic as `_validate_add` for category and amount (by calling the existing helper or duplicating the checks inline in the importer for separation of concerns).
- Date validation uses `date.fromisoformat()` catching `ValueError`.
- Collect ALL errors before returning — do not stop at first error.

## Atomicity

The write is: load existing → append → save (same as `cmd_add`). If save raises an exception, the ledger file is not modified (the existing `store.save` writes to a tmp file and renames). This is already safe.

**Design decision made by hand (edited from agent draft):** The agent initially proposed using `csv.reader` with positional columns. Changed to `csv.DictReader` so column order in the CSV file does not matter — the requirements specify columns can be in any order. This is a meaningful difference and was not in the initial generated draft.
