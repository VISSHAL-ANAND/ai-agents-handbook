# Tasks: CSV import

Each task follows the test-first pattern: write failing tests, then implement, then verify.

## Task 1: importer module — parse and validate CSV

**Files touched:** `src/ledgerlite/importer.py` (new), `tests/test_importer.py` (new)

Implement `parse_csv(path: Path) -> tuple[list[Entry], list[str]]`.

Tests (write first):
- `test_parse_valid_csv`: well-formed CSV → correct entries, no errors
- `test_parse_invalid_amount`: non-numeric amount → error list contains row reference
- `test_parse_negative_amount`: negative amount → error
- `test_parse_empty_category`: blank category → error
- `test_parse_invalid_date`: bad date format → error
- `test_parse_multiple_errors`: CSV with several bad rows → all errors reported, not just first
- `test_parse_column_order`: columns in non-standard order → still works

Commit: `test(importer): failing tests for parse_csv`
Then implement, verify, commit: `feat(importer): parse_csv validates all rows`

## Task 2: CLI import command

**Files touched:** `src/ledgerlite/cli.py`, `tests/test_cli.py`

Add `cmd_import` and wire it into `build_parser`.

Tests (write first):
- `test_import_valid_csv`: valid CSV → entries appended, "imported N entries" printed, exit 0
- `test_import_file_not_found`: missing file → error on stderr, exit 2, ledger unchanged
- `test_import_invalid_rows`: CSV with bad rows → all errors on stderr, exit 2, ledger unchanged (no partial write)
- `test_import_empty_csv`: empty/header-only → error, exit 2
- `test_import_duplicate_skipped`: row matching existing entry → warning, import still succeeds

Commit: `test(cli): failing tests for import command`
Then implement, verify, commit: `feat(cli): add import subcommand`

## Task 3: integration and edge cases

**Files touched:** `tests/test_importer.py`, `tests/test_cli.py`

Add characterization/edge-case tests:
- `test_import_preserves_existing_entries`: existing ledger entries are not modified
- `test_import_decimal_precision`: amount with many decimal places stored exactly
- `test_import_mixed_valid_invalid`: mix of good and bad rows → nothing written

Commit: `test(importer): edge case and integration tests`
Verify VERIFY PASS.
