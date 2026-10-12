1. The naive prompt, `fix validation in add`, did not specify the exact validation rules, required test cases, or a strict file-change limit.
2. The naive run expanded scope by adding extra invalid-date and invalid-amount-text handling, beyond the intended requirements.
3. In Round 2, the brief's explicit rules, required four tests in `tests/test_cli.py`, and "Do not change any other file" constraint kept the implementation focused.
4. I would merge the with-skill run because the agent explicitly followed the migration procedure: bump the schema version, register a v1-to-v2 migration, add a legacy fixture and migration test, and require `currency` in `from_dict` rather than hiding a missing migration with a default.
5. Without a proper migration, old ledger files could fail to load when `from_dict` requires `currency`. Using a default in `from_dict` without a schema migration could also hide future schema changes and leave the on-disk format inconsistent.
6. The comparison was not a perfectly isolated experiment: in the no-skill run, I explicitly allowed the agent to read the disabled skill as reference material after it initially refused to proceed. The with-skill run used a fresh session and automatically followed the skill. I should account for this limitation when interpreting the result.


## Chapter 5 — Phase 0: Category budgets acceptance criteria

**Criterion 1 — Ubiquitous (storage format)**
The system shall store budgets in the ledger file under a `budgets` key mapping category to a Decimal amount.

**Criterion 2 — Event-driven (`budget set`)**
WHEN the user runs `budget set <category> <amount>` the system shall persist the budget and print `budget <category> set to <amount>`.

**Criterion 3 — Event-driven (`budget status`)**
WHEN the user runs `budget status --year Y --month M`, the system shall print one line per budgeted category showing the budget amount, the month's total spend, and the remaining amount (budget minus spent), and exit with code 0.
*(Open for design phase: exact output format — column layout, labels, ordering.)*

**Criterion 4 — Unwanted (invalid amount)**
IF the `<amount>` argument to `budget set` is not a positive Decimal (zero, negative, non-numeric, or non-finite), THEN the system shall print `error: amount must be positive` to stderr, exit with code 2, and leave the ledger file unchanged.
*(Open for design phase: whether error message wording must match `add` exactly.)*

**Criterion 5 — State-driven (over-budget warning)**
WHILE the total spend for the category and calendar month of the newly added entry is strictly greater than (not equal to) that category's budget, the system shall print a warning to stderr after a successful `add` and exit with code 0.
*(Open for design phase: exact warning message text and format.)*

**Criterion 6 — Optional (no budget set)**
WHERE no budget has been set for a category, `budget status` shall omit that category from its output and exit with code 0.
*(Open for design phase: what to print when no budgets exist at all.)*
