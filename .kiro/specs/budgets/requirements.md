# Requirements: category budgets

Source of truth: six EARS-pattern acceptance criteria approved in NOTES.md (Chapter 5, Phase 0).
Open questions are listed at the bottom and deferred to the design phase.

## Overview

A user sets a monthly spending budget per category. The CLI reports actual spend against each
budget for a given month, and warns when a new expense causes a category's spending to strictly
exceed its budget for that calendar month.

## User stories

### US-1: Set a budget
As a user, I want to set a monthly spending limit for a category so that I can track whether I
am overspending.

### US-2: View budget status
As a user, I want to see each category's budget, total spend, and remaining amount for a given
month so that I know where I stand.

### US-3: Over-budget warning on add
As a user, I want to be warned immediately when adding an expense causes a category's total
spending for that month to strictly exceed its budget, so that I notice overspending as it happens.

## Acceptance criteria

### AC-1 — Storage format (maps to Criterion 1)
The system shall store budgets in the ledger file under a `budgets` key, mapping category name
(string) to budget amount (stored as a string in JSON, read as Decimal). Budgets shall survive a
save/load round-trip without data loss.

**Testable:** Write a ledger file containing a `budgets` key with known values; load it; assert
the values are present and correct. Save and reload; assert values are unchanged.

### AC-2 — `budget set` persists and confirms (maps to Criterion 2)
WHEN the user runs `budget set <category> <amount>`, the system shall persist the budget in the
ledger file and print `budget <category> set to <amount>` to stdout, then exit with code 0.

**Testable:** Run `budget set food 5000`; assert exit code 0, stdout contains
`budget food set to 5000`, and the ledger file contains the budget for `food`.

### AC-3 — `budget status` reports per category (maps to Criterion 3)
WHEN the user runs `budget status --year Y --month M`, the system shall print one line per
budgeted category showing the budget amount, the total spend for that month, and the remaining
amount (budget minus spent), then exit with code 0. Remaining may be negative when spending
exceeds budget.

**Testable:** Set a budget for `food`; add entries in the target month totalling a known amount;
run `budget status --year Y --month M`; assert the budget, spent, and remaining values for `food`
appear in the output.

### AC-4 — Invalid amount rejected (maps to Criterion 4)
IF the `<amount>` argument to `budget set` is not a positive Decimal (zero, negative,
non-numeric, or non-finite), THEN the system shall print `error: amount must be positive` to
stderr, exit with code 2, and leave the ledger file unchanged.

**Testable:** Run `budget set food 0`, `budget set food -1`, and `budget set food abc`; for each,
assert exit code 2, stderr contains `error: amount must be positive`, and the ledger file is
identical to its state before the command ran.

### AC-5 — Over-budget warning on `add` (maps to Criterion 5)
WHILE the total spend for the category and calendar month of the newly added entry is strictly
greater than that category's budget, the system shall print a warning to stderr. The `add`
command shall save the entry and exit with code 0.

The calendar month is derived from the `--day` argument of the new entry (defaulting to today).
The comparison is strict: total spend equal to the budget does not trigger a warning.

**Testable:** Set a budget of 100 for `food`. Add entries totalling exactly 100 for `food` in
month M; assert no warning. Add one more entry for `food` in month M (total now > 100); assert
exit code 0, the entry is saved, and stderr contains a warning.

### AC-6 — Categories with no budget omitted from status (maps to Criterion 6)
WHERE no budget has been set for a category, `budget status` shall omit that category from its
output and exit with code 0.

**Testable:** Run `budget status` with entries for `food` but no budget set for `food`; assert
`food` does not appear in the output and exit code is 0.

## Migration requirement

Adding a `budgets` key to the ledger file is a schema change. The implementation must follow
every step in `.kiro/skills/ledgerlite-migration/SKILL.md`:

1. `SCHEMA_VERSION` in `src/ledgerlite/store.py` must be bumped by exactly one from the
   baseline on `main`. The resulting version is a design decision; this document does not
   assume a specific number.
2. A migration function registered in `MIGRATIONS` must upgrade files written at the previous
   version to the new layout. The function must be pure and must not read the filesystem.
3. `src/ledgerlite/models.py` must not hide a missing migration with a `.get(..., default)`
   fallback; required keys are read directly.
4. A fixture file in the previous layout (at least two entries, no `budgets` key) must be
   added under `fixtures/`.
5. A test in `tests/test_store.py` must load the fixture, assert the migrated values, save to
   a temp path, and assert `schema_version` equals the new value in the written file.

The invariant from the skill applies without exception: any ledger file written by any earlier
version of ledgerlite must load without data loss after this change. Existing entries must be
preserved exactly.

## Out of scope

- Budget periods other than calendar months.
- Multiple currencies.
- Deleting or listing all existing budgets.
- Suppressing the over-budget warning via a flag.

## Open questions (deferred to design phase)

| # | Question |
|---|---|
| OQ-1 | Does `budget set` silently overwrite an existing budget, error, or prompt for confirmation? |
| OQ-2 | What does `budget status` print when no budgets have been set at all (empty output, a message, or non-zero exit)? |
| OQ-3 | Exact output format for `budget status` — column layout, labels, alignment, ordering of categories. |
| OQ-4 | Exact text and format of the over-budget warning printed to stderr by `add`. |
| OQ-5 | Does `budget set` validate that the category string is non-empty or non-whitespace, consistent with `add`? |
| OQ-6 | What is the resulting `SCHEMA_VERSION` after this migration? Depends on whether any other schema changes (e.g. `currency` from `ch4-with-skill`) are merged to `main` before this feature. Design must verify `SCHEMA_VERSION` on `main` before choosing the next value. |
