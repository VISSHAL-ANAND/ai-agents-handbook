# Tasks: category budgets

Implements `.kiro/specs/budgets/requirements.md` and `.kiro/specs/budgets/design.md`.
Verification command for every task: `python scripts/verify.py` must print `VERIFY PASS`.

Execute tasks in order. Task 1 must be complete and verified before Task 2 begins.

---

## Task 1 — Schema migration: add `budgets` to the ledger file

**Why first:** Tasks 2–4 all depend on the `budgets` key existing in the ledger and on
`store.load_budgets` / `store.save_budgets` being available. The migration must land first.

**Files touched (3):**
- `src/ledgerlite/store.py`
- `fixtures/ledger_v1.json` (new)
- `tests/test_store.py`

**Changes:**
1. In `store.py`:
   - Bump `SCHEMA_VERSION` from 1 to 2.
   - Add `_migrate_v1_to_v2(data)` — pure function, adds `"budgets": {}` if key absent.
   - Register `MIGRATIONS[1] = _migrate_v1_to_v2`.
   - Modify `store.save()` body to read existing `budgets` from disk before writing (no
     `try/except` — let corrupt files raise). Write `budgets` in every save payload.
   - Add `load_budgets(path) -> dict[str, Decimal]`.
   - Add `save_budgets(path, budgets)` — reads full file, patches `budgets` key, atomic write.

2. Create `fixtures/ledger_v1.json` — real v1 file, two entries, no `budgets` key:
   ```json
   {
     "schema_version": 1,
     "entries": [
       {"day": "2026-01-05", "category": "rent", "amount": "15000"},
       {"day": "2026-01-06", "category": "food", "amount": "250.25"}
     ]
   }
   ```

3. In `tests/test_store.py` add:
   - `test_migrate_v1_adds_budgets` — load fixture, assert 2 entries, `budgets == {}`,
     save to tmp, assert `schema_version == 2` and `budgets == {}` in written file.
   - `test_budgets_round_trip` — `save_budgets` then `load_budgets` returns same Decimal values.
   - `test_save_preserves_budgets` — `save_budgets`, then `store.save(entries)`, reload budgets
     — still present.
   - `test_save_budgets_preserves_entries` — `store.save(entries)`, then `save_budgets(budgets)`,
     reload entries — still present.
   - `test_save_corrupt_ledger_raises` — write corrupt JSON, call `store.save(path, entries)`,
     assert raises `ValueError` or `JSONDecodeError`, assert original file unchanged.

**Verification:** `python scripts/verify.py` → `VERIFY PASS`
**Commit:** `feat(budget): task 1, schema migration and budget storage`

---

## Task 2 — CLI: `budget set` command

**Depends on:** Task 1 (requires `load_budgets`, `save_budgets`).

**Files touched (2):**
- `src/ledgerlite/cli.py`
- `tests/test_cli.py`

**Changes:**
1. In `cli.py`:
   - Add `cmd_budget_set(args)` — validates category (non-empty after strip) and amount
     (reuse `_validate_add`); loads budgets, sets `budgets[category] = Decimal(amount)`,
     saves, prints `budget <category> set to <amount>`, returns 0.
   - Add `budget` subcommand and `set` sub-subcommand to `build_parser()`.

2. In `tests/test_cli.py` add:
   - `test_budget_set_persists` — exit 0, stdout contains `budget food set to 5000`.
   - `test_budget_set_overwrites` — set food=5000, then food=3000; assert 3000 persists.
   - `test_budget_set_zero_amount` — exit 2, stderr `error: amount must be positive`,
     ledger unchanged.
   - `test_budget_set_negative_amount` — exit 2, stderr message, ledger unchanged.
   - `test_budget_set_invalid_amount` — exit 2, stderr message, ledger unchanged.
   - `test_budget_set_empty_category` — exit 2, stderr `error: category is required`,
     ledger unchanged.

**Verification:** `python scripts/verify.py` → `VERIFY PASS`
**Commit:** `feat(budget): task 2, budget set command`

---

## Task 3 — CLI: `budget status` command

**Depends on:** Task 2 (requires `budget` subcommand scaffold in `build_parser`).

**Files touched (2):**
- `src/ledgerlite/cli.py`
- `tests/test_cli.py`

**Changes:**
1. In `cli.py`:
   - Add `_month_last_day(year, month)` helper — handles December (`date(year, 12, 31)`)
     and all other months.
   - Add `cmd_budget_status(args)` — wraps date construction in `try/except ValueError`
     (prints `error: invalid year/month` to stderr, returns 2 on failure); loads budgets;
     if empty prints `no budgets set` and returns 0; loads entries, filters by month using
     `_month_last_day`, computes totals via `report.totals_by_category`; prints one labelled
     line per budgeted category (alphabetical), exits 0.
   - Register `status` sub-subcommand under `budget` in `build_parser()`.

2. In `tests/test_cli.py` add:
   - `test_budget_status_shows_values` — budget/spent/remaining in output, exit 0.
   - `test_budget_status_negative_remaining` — remaining negative when spent > budget.
   - `test_budget_status_no_budgets` — stdout `no budgets set`, exit 0.
   - `test_budget_status_omits_unbudgeted` — unbudgeted category absent from output.
   - `test_budget_status_december` — `--year 2026 --month 12`, exit 0, no crash.
   - `test_budget_status_invalid_month` — `--month 13`, exit 2, stderr `error: invalid year/month`.
   - `test_budget_status_invalid_year` — `--year 0 --month 1`, exit 2, stderr message.

**Verification:** `python scripts/verify.py` → `VERIFY PASS`
**Commit:** `feat(budget): task 3, budget status command`

---

## Task 4 — CLI: over-budget warning in `add`

**Depends on:** Task 1 (requires `load_budgets`).

**Files touched (2):**
- `src/ledgerlite/cli.py`
- `tests/test_cli.py`

**Changes:**
1. In `cli.py`, extend `cmd_add`:
   - After saving the entry and printing the confirmation, call `store.load_budgets(args.ledger)`.
   - If the category has a budget, compute monthly totals via `report.entries_in_month` and
     `report.totals_by_category` using the updated `entries` list (includes new entry).
   - If `total > budget` (strict), print
     `warning: <category> over budget for <YYYY-MM>` to stderr.
   - Return 0 regardless.

2. In `tests/test_cli.py` add:
   - `test_add_no_warning_at_exact_budget` — total == budget, exit 0, stderr empty.
   - `test_add_warns_when_over_budget` — total > budget, exit 0, entry saved, stderr contains
     `over budget` and `YYYY-MM`.
   - `test_add_no_warning_no_budget_set` — no budget for category, exit 0, stderr empty.

**Verification:** `python scripts/verify.py` → `VERIFY PASS`
**Commit:** `feat(budget): task 4, over-budget warning in add`
