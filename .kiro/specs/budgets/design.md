# Design: category budgets

Implements `.kiro/specs/budgets/requirements.md` (commit `0e99f9d`).
Baseline: `main` at `SCHEMA_VERSION = 1`, no `currency` field, no other pending migrations.

## Design decisions

| ID | Decision |
|----|----------|
| D-1 | `budget set` silently overwrites an existing category budget. |
| D-2 | `budget status` with no budgets configured prints `no budgets set` to stdout, exits 0. |
| D-3 | Status prints one labelled line per budgeted category, sorted alphabetically, with budget, spent, and remaining. |
| D-4 | Over-budget warning goes to stderr, includes category and `YYYY-MM`. Strict `>`; equality is silent. |
| D-5 | Empty or whitespace-only category in `budget set` is rejected with `error: category is required` to stderr, exit 2. |
| D-6 | `SCHEMA_VERSION` on `main` is 1 (verified). Target version is 2. |
| D-7 | Additive store API: new `load_budgets` / `save_budgets` helpers. Existing `load` / `save` signatures unchanged. |
| D-8 | Nested CLI subcommands: `ledgerlite budget set` and `ledgerlite budget status`. |
| D-9 | All CLI handlers stay in `cli.py`. No new modules. |

---

## Architecture and data flow

### `budget set <category> <amount>`

```
cli.py: cmd_budget_set(args)
  │
  ├─ validate category (non-empty after strip) → stderr + exit 2 on failure
  ├─ validate amount (_validate_add reused) → stderr + exit 2 on failure
  │
  ├─ store.load_budgets(args.ledger) → dict[str, Decimal]
  ├─ budgets[category] = Decimal(amount)   # D-1: silent overwrite
  ├─ store.save_budgets(args.ledger, budgets)
  └─ print("budget <category> set to <amount>") → stdout, return 0
```

### `budget status --year Y --month M`

```
cli.py: cmd_budget_status(args)
  │
  ├─ store.load_budgets(args.ledger) → dict[str, Decimal]
  │
  ├─ if empty → print("no budgets set"), return 0   # D-2
  │
  ├─ store.load(args.ledger) → list[Entry]
  ├─ report.entries_in_month(entries, year, month) → list[Entry]
  ├─ report.totals_by_category(month_entries) → dict[str, Decimal]  # sorted alphabetically
  │
  └─ for category in sorted(budgets):   # D-3: alphabetical order
       spent = totals.get(category, Decimal("0"))
       remaining = budget - spent
       print one labelled line
     return 0
```

### `add` over-budget warning

```
cli.py: cmd_add(args)
  │
  ├─ [existing validation: category, amount]
  ├─ store.load(args.ledger) → list[Entry]
  ├─ append new Entry
  ├─ store.save(args.ledger, entries)      # entry saved first; warning is advisory
  ├─ print("added ...") → stdout
  │
  ├─ store.load_budgets(args.ledger) → dict[str, Decimal]
  ├─ if category in budgets:
  │     month_entries = report.entries_in_month(entries, day.year, day.month)
  │     totals = report.totals_by_category(month_entries)
  │     if totals.get(category, Decimal("0")) > budgets[category]:   # D-4: strict >
  │         print("warning: <category> over budget for <YYYY-MM>", file=sys.stderr)
  └─ return 0   # always 0 on successful add
```

The entry is saved before the budget check. The warning is advisory; it never prevents saving.

---

## Ledger JSON structure (schema version 2)

```json
{
  "schema_version": 2,
  "entries": [
    {"day": "2026-01-05", "category": "rent", "amount": "15000"}
  ],
  "budgets": {
    "food": "5000",
    "rent": "15000"
  }
}
```

- Budget amounts are stored as strings (matching `amount` in entries).
- A file with no budgets has `"budgets": {}`.
- Schema version 1 files have no `budgets` key; migration adds `"budgets": {}`.

---

## Storage API changes (D-7)

### Critical constraint: `store.save()` must preserve `budgets`

**Verified from `store.py`:** the current `store.save()` writes only
`{"schema_version": ..., "entries": [...]}`. It does not include `budgets`. If `cmd_add` calls
`store.save(path, entries)` after a budget has been set, the `budgets` key is silently dropped
from the file. This makes the additive-only approach unsafe unless `store.save()` is also fixed.

### Chosen approach: fix `store.save()` to round-trip `budgets`

`store.save()` will be modified to preserve the `budgets` key if one exists on disk, and to
write `"budgets": {}` otherwise. This is the minimal change: the function signature
(`path`, `entries`) is unchanged and all existing callers continue to work without modification.

```python
def save(path: Path, entries: list[Entry]) -> None:
    """Save entries, preserving budgets if already present in the file."""
    # Read existing budgets to preserve them; default to empty only when file is absent.
    # If the file exists but cannot be read or parsed, raise — do not silently overwrite
    # a ledger that may contain budget data we cannot read.
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing = _migrate(existing)
        budgets = existing.get("budgets", {})
    else:
        budgets = {}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "entries": [e.to_dict() for e in entries],
        "budgets": budgets,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
```

This change means:
- Existing tests (`test_save_then_load` etc.) continue to pass: the `entries` round-trip is
  unaffected; `budgets` is just an additional key.
- `cmd_add`, `cmd_list`, `cmd_report` callers are not modified.
- A ledger file written by the new `save()` always contains both `entries` and `budgets`.
- A corrupt existing ledger raises (propagates `json.JSONDecodeError` or `ValueError`), which
  is consistent with the existing behavior of `store.load()` — it also raises on a corrupt file
  and does not silently recover. Budget data is never silently replaced with `{}`.

### New functions in `store.py`

```python
def load_budgets(path: Path) -> dict[str, Decimal]:
    """Return budgets dict. Missing file or missing key returns empty dict."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    data = _migrate(data)
    return {k: Decimal(v) for k, v in data.get("budgets", {}).items()}


def save_budgets(path: Path, budgets: dict[str, Decimal]) -> None:
    """Write budgets into the ledger file, preserving entries and schema_version."""
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data = _migrate(data)
    else:
        data = {"schema_version": SCHEMA_VERSION, "entries": []}
    data["budgets"] = {k: str(v) for k, v in budgets.items()}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)
```

`load_budgets`: returns `{}` for missing file or missing `budgets` key. Always runs `_migrate`
so it operates on the current schema regardless of on-disk version.

`save_budgets`: reads existing file first (to preserve `entries`), migrates it, patches only
the `budgets` key, writes atomically via `.tmp` + `replace`. If the file is missing, starts
with empty entries.

### Preservation guarantees

| Operation | entries preserved? | budgets preserved? |
|-----------|-------------------|--------------------|
| `store.save(path, entries)` | ✓ written | ✓ read from disk and re-written |
| `store.save_budgets(path, budgets)` | ✓ read from disk and re-written | ✓ written |
| `store.load(path)` | ✓ returned | not in return value (not needed) |
| `store.load_budgets(path)` | not in return value (not needed) | ✓ returned |

Both write operations read-then-write the full JSON atomically, so neither can silently discard
the other section.

---

## Migration (D-6)

Follows `.kiro/skills/ledgerlite-migration/SKILL.md` step by step.

### Step 1: bump `SCHEMA_VERSION`

```python
# src/ledgerlite/store.py
SCHEMA_VERSION = 2
```

### Step 2: register migration function

```python
def _migrate_v1_to_v2(data: dict) -> dict:
    """Add budgets key (empty dict) to files that lack it."""
    if "budgets" not in data:
        data["budgets"] = {}
    return data

MIGRATIONS[1] = _migrate_v1_to_v2
```

The function is pure and reads no filesystem state.

### Step 3: `models.py` — no change required

`Entry` fields are not changing. `to_dict` and `from_dict` are not affected. No `.get()` defaults
are introduced.

### Step 4: fixture

`fixtures/ledger_v1.json` — a real v1 file with at least two entries, no `budgets` key:

```json
{
  "schema_version": 1,
  "entries": [
    {"day": "2026-01-05", "category": "rent", "amount": "15000"},
    {"day": "2026-01-06", "category": "food", "amount": "250.25"}
  ]
}
```

### Step 5: migration test

In `tests/test_store.py`:

```python
def test_migrate_v1_adds_budgets(tmp_path):
    entries = store.load(FIXTURES / "ledger_v1.json")
    assert len(entries) == 2  # entries preserved
    budgets = store.load_budgets(FIXTURES / "ledger_v1.json")
    assert budgets == {}  # no budgets in v1

    store.save(tmp_path / "out.json", entries)
    data = json.loads((tmp_path / "out.json").read_text())
    assert data["schema_version"] == 2
    assert data["budgets"] == {}
```

### Step 6: verify

`python scripts/verify.py` must print `VERIFY PASS` before the task is reported done.

---

## CLI subcommand structure (D-8, D-9)

```python
# In build_parser(), after existing subcommands:

b = sub.add_parser("budget", help="manage category budgets")
b.set_defaults(func=lambda args: (
    build_parser().parse_args(["budget", "--help"]), 0
)[1])  # fallback if no subcommand given
bsub = b.add_subparsers(dest="budget_command", required=True)

bs = bsub.add_parser("set", help="set a category budget")
bs.add_argument("category")
bs.add_argument("amount")
bs.set_defaults(func=cmd_budget_set)

bst = bsub.add_parser("status", help="show budget vs. spend")
bst.add_argument("--year", type=int, required=True)
bst.add_argument("--month", type=int, required=True)
bst.set_defaults(func=cmd_budget_status)
```

Both `cmd_budget_set` and `cmd_budget_status` are defined in `cli.py` alongside existing handlers.

---

## Validation and error handling

### `budget set` validation

| Condition | Output | Exit |
|-----------|--------|------|
| Category empty or whitespace-only | `error: category is required` → stderr | 2 |
| Amount zero, negative, non-numeric, non-finite | `error: amount must be positive` → stderr | 2 |
| Valid | persist budget, `budget <cat> set to <amt>` → stdout | 0 |

Reuses `_validate_add(category, amount)` from the existing `cmd_add` path (the helper already
handles both checks and returns the error tuple or `None`).

### `budget status` validation

argparse enforces `--year` and `--month` as required integers. No additional validation needed.

### `add` warning

No change to `add` exit codes. A successful add always exits 0. Warning is informational only.

---

## Output format (D-3)

### `budget status` — one line per budgeted category, alphabetical order

```
food        budget: 5000.00   spent: 3200.00   remaining: 1800.00
rent        budget: 15000.00  spent: 15000.00  remaining: 0.00
transport   budget: 2000.00   spent: 2500.00   remaining: -500.00
```

- Category name left-aligned, 16 characters wide.
- Each value labelled (`budget:`, `spent:`, `remaining:`), right-aligned to 10 characters.
- Remaining is `budget - spent`; negative means over budget.
- Alphabetical order is produced by `sorted(budgets)`, consistent with `totals_by_category`.

### `budget status` — no budgets

```
no budgets set
```

### Over-budget warning (D-4)

```
warning: food over budget for 2026-10
```

Printed to stderr. Month formatted as `YYYY-MM` using `f"{day.year}-{day.month:02d}"`.

---

## Test plan

| AC | Test | File | What is asserted |
|----|------|------|-----------------|
| AC-1 | `test_budgets_round_trip` | `test_store.py` | `save_budgets` then `load_budgets` returns same values |
| AC-2 | `test_budget_set_persists` | `test_cli.py` | exit 0, stdout contains message, ledger has budget |
| AC-3 | `test_budget_status_shows_values` | `test_cli.py` | budget/spent/remaining appear in output; exit 0 |
| AC-4a | `test_budget_set_zero_amount` | `test_cli.py` | exit 2, stderr message, ledger unchanged |
| AC-4b | `test_budget_set_negative_amount` | `test_cli.py` | exit 2, stderr message, ledger unchanged |
| AC-4c | `test_budget_set_invalid_amount` | `test_cli.py` | exit 2, stderr message, ledger unchanged |
| AC-5a | `test_add_no_warning_at_exact_budget` | `test_cli.py` | exit 0, stderr empty when total == budget |
| AC-5b | `test_add_warns_when_over_budget` | `test_cli.py` | exit 0, entry saved, stderr contains warning |
| AC-6a | `test_budget_status_omits_unbudgeted` | `test_cli.py` | unbudgeted category absent from output |
| AC-6b | `test_budget_status_no_budgets` | `test_cli.py` | stdout is `no budgets set`, exit 0 |
| Migration | `test_migrate_v1_adds_budgets` | `test_store.py` | fixture loads, entries preserved, `schema_version == 2` |

All tests use `tmp_path` (pytest fixture) and `capsys` for output capture. No real files modified.

---

## Compatibility with existing commands

- `cmd_add`, `cmd_list`, `cmd_report` — unchanged. They call `store.load()` and `store.save()`,
  which now write `schema_version: 2` and `budgets: {}` on first save, but the `entries` key
  and its contents are identical.
- Existing tests `test_save_then_load`, `test_add_then_list`, `test_report_command` — unaffected.
  The only store change is `SCHEMA_VERSION` bump and new migration; `load()` and `save()` behavior
  for entries is identical.
- `test_models.py` — unaffected; `Entry` is unchanged.
- `test_report.py` — unaffected; `report.py` is unchanged.

---

## December and invalid month/year handling

### The bug (verified)

`report.month_range(year, month)` computes:
```python
last = date(year, month + 1, 1) - timedelta(days=1)
```
For `month=12`, this calls `date(year, 13, 1)`, which raises `ValueError`. This affects the
existing `cmd_report` command too, but fixing `cmd_report` is out of scope here.

### Resolution for `cmd_budget_status`

`cmd_budget_status` will **not** call `report.month_range` or `report.entries_in_month` directly.
Instead, it will use a local helper `_entries_in_month_safe` that handles December correctly:

```python
def _month_last_day(year: int, month: int) -> date:
    """Last calendar day of any month, including December."""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)
```

This helper is defined in `cli.py` (no new module). `cmd_budget_status` uses it directly
alongside `date(year, month, 1)` for the first day.

`cmd_report` is **not changed** — it retains the existing December bug to avoid unintended
scope creep. This is documented as a known limitation.

### Invalid month/year values

argparse declares `--year` and `--month` as `type=int`. If the user passes a non-integer,
argparse rejects it with its own error message before the handler runs.

If the user passes an out-of-range value (e.g. `--month 0` or `--month 13`), `date(year, month, 1)`
raises `ValueError`. `cmd_budget_status` will catch this and print
`error: invalid year/month` to stderr, exit 2.

```python
try:
    first = date(args.year, args.month, 1)
    last = _month_last_day(args.year, args.month)
except ValueError:
    print("error: invalid year/month", file=sys.stderr)
    return 2
```

This guard is **only added to `cmd_budget_status`**. `cmd_report` is not changed.


## `_validate_add` reuse (D-5, confirmed)

**Verified from `cli.py`:** `_validate_add(category: str, amount: str)` performs exactly two checks:
1. `if not category.strip()` → returns `("error: category is required", 2)`
2. Parses `Decimal(amount)`, checks `is_finite()` and `> 0` → returns `("error: amount must be positive", 2)`
3. Returns `None` if both pass.

The function name references `add` but contains no `add`-specific logic. It is safe to call from
`cmd_budget_set` with the same argument types. No modification needed.

---

## Updated test plan

| AC / concern | Test name | File | What is asserted |
|---|---|---|---|
| AC-1 | `test_budgets_round_trip` | `test_store.py` | `save_budgets` then `load_budgets` returns same Decimal values |
| AC-1 | `test_save_preserves_budgets` | `test_store.py` | after `save_budgets`, call `store.save(entries)`, reload budgets — still present |
| AC-1 | `test_save_budgets_preserves_entries` | `test_store.py` | after `store.save(entries)`, call `save_budgets(budgets)`, reload entries — still present |
| AC-2 | `test_budget_set_persists` | `test_cli.py` | exit 0, stdout contains `budget food set to 5000`, ledger has budget |
| AC-2 | `test_budget_set_overwrites` | `test_cli.py` | set food=5000, then set food=3000; `load_budgets` returns 3000 |
| AC-3 | `test_budget_status_shows_values` | `test_cli.py` | budget/spent/remaining values appear in output; exit 0 |
| AC-3 | `test_budget_status_december` | `test_cli.py` | `--year 2026 --month 12` runs without error; exit 0 |
| AC-3 | `test_budget_status_negative_remaining` | `test_cli.py` | remaining is negative when spent > budget |
| AC-4a | `test_budget_set_zero_amount` | `test_cli.py` | exit 2, stderr `error: amount must be positive`, ledger unchanged |
| AC-4b | `test_budget_set_negative_amount` | `test_cli.py` | exit 2, stderr message, ledger unchanged |
| AC-4c | `test_budget_set_invalid_amount` | `test_cli.py` | exit 2, stderr message, ledger unchanged |
| AC-4d | `test_budget_set_empty_category` | `test_cli.py` | exit 2, stderr `error: category is required`, ledger unchanged |
| AC-5a | `test_add_no_warning_at_exact_budget` | `test_cli.py` | exit 0, stderr empty when total == budget |
| AC-5b | `test_add_warns_when_over_budget` | `test_cli.py` | exit 0, entry saved, stderr contains `over budget` and `YYYY-MM` |
| AC-5c | `test_add_no_warning_no_budget_set` | `test_cli.py` | exit 0, stderr empty when no budget for category |
| AC-6a | `test_budget_status_omits_unbudgeted` | `test_cli.py` | unbudgeted category absent from output |
| AC-6b | `test_budget_status_no_budgets` | `test_cli.py` | stdout is `no budgets set`, exit 0 |
| Invalid input | `test_budget_status_invalid_month` | `test_cli.py` | `--month 13` → exit 2, stderr `error: invalid year/month` |
| Invalid input | `test_budget_status_invalid_year` | `test_cli.py` | `--year 0 --month 1` → exit 2, stderr `error: invalid year/month` |
| Error handling | `test_save_corrupt_ledger_raises` | `test_store.py` | write corrupt JSON to ledger, call `store.save(path, entries)` → raises `ValueError` or `JSONDecodeError`; original file not overwritten |
| Migration | `test_migrate_v1_adds_budgets` | `test_store.py` | fixture loads, 2 entries preserved, `schema_version == 2`, `budgets == {}` |

All tests use `tmp_path` and `capsys`. No real files modified.

---

## Remaining assumptions and open questions

| # | Item | Status |
|---|------|--------|
| A-1 | `_validate_add` is reusable for `budget set`. | Confirmed by code inspection. Generic logic; no `add`-specific behavior. |
| A-2 | `store.save()` signature `(path, entries)` is unchanged. | The body changes to round-trip `budgets`, but the signature and all callers are unaffected. |
| A-3 | Double file read in `cmd_add` (`store.save` reads existing budgets; then `load_budgets` reads again). | Acceptable for a personal ledger tool. No caching introduced. |
| A-4 | `cmd_report` December bug is out of scope. | Known limitation; not fixed here to avoid unintended scope. |
| A-5 | Corrupt ledger raises on `store.save()`. | Consistent with `store.load()` behavior. Budget data is never silently replaced with `{}`. |
| OQ-remaining | All six original open questions from requirements.md are resolved. | No open questions remain. |
