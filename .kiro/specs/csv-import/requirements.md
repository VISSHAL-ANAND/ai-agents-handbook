# Requirements: CSV import

## Overview

Add an `import` subcommand to ledgerlite that reads a CSV file and appends validated entries to the ledger. The command must validate all rows before writing any, report every error, and never produce a partial write.

## Functional requirements

1. The command is invoked as: `ledgerlite import [--ledger FILE] <csvfile>`
2. The CSV file must have a header row with columns `day`, `category`, and `amount` (any order).
3. Each data row is validated with the same rules as `add`: amount must be a positive finite Decimal, category must be non-empty, day must be a valid ISO date (YYYY-MM-DD).
4. If any row fails validation, print all errors to stderr with 1-based row numbers, write nothing, and exit 2.
5. If the CSV file does not exist, print `error: file not found: <path>` to stderr and exit 2.
6. If the CSV file is empty or contains only a header, print `error: no data rows in <path>` to stderr and exit 2.
7. If all rows are valid, append them to the existing ledger and print `imported N entries` to stdout, exit 0.
8. Duplicate detection: a row that exactly matches (day + category + amount) an existing ledger entry is skipped with a per-row warning to stderr; the import still succeeds (exit 0) for the non-duplicate rows.

## Non-functional requirements

- Amounts are stored as Decimal, never float (existing project convention).
- The import is atomic: either all new (non-duplicate) rows are written, or nothing is written.
- No network calls. No schema version change is required (no new fields on Entry).
- All new behaviour must be covered by tests. No existing tests may be weakened.

## Out of scope

- Quoted fields with commas inside values (not needed for `day,category,amount`).
- Any output format other than the existing ledger JSON.
- Overwriting or replacing existing entries.
