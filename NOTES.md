# NOTES.md — AI Coding Agents Handbook

## Chapter 11 — Capstone: CSV import

### Feature: CSV import

`import file.csv` reads `day,category,amount` rows, validates every row, reports all errors before writing anything, and writes only if all rows are valid.

### Six EARS acceptance criteria

**Criterion 1 — Ubiquitous (input format)**
The system shall accept a CSV file with a header row containing exactly the columns `day`, `category`, and `amount` in any order; rows that do not conform to this format are treated as validation errors.

**Criterion 2 — Event-driven (successful import)**
WHEN the user runs `import <file.csv>` and all rows are valid, the system shall append the new entries to the ledger file, print `imported N entries` to stdout, and exit with code 0.

**Criterion 3 — Unwanted (any row invalid — no partial write)**
IF any row in the CSV file fails validation (non-positive or non-numeric amount, empty category, invalid date format, or missing required column), THEN the system shall print every error to stderr with the row number, write nothing to the ledger file, and exit with code 2.

**Criterion 4 — Unwanted (file not found)**
IF the CSV file path does not exist, THEN the system shall print `error: file not found: <path>` to stderr and exit with code 2 without modifying the ledger.

**Criterion 5 — State-driven (idempotency guard)**
WHILE the CSV file contains a row whose `day`, `category`, and `amount` exactly match an entry already in the ledger, the system shall report a warning for that row but still write the remaining unique entries and exit with code 0.
*(Open for design phase: whether duplicate detection is exact-match only or approximate.)*

**Criterion 6 — Unwanted (empty file or header-only)**
IF the CSV file is empty or contains only a header row with no data rows, THEN the system shall print `error: no data rows in <path>` to stderr and exit with code 2.

*Ambiguity noted and resolved before implementation: Criterion 5 (duplicate handling) initially said "report a warning" without specifying whether duplicates block the import or just warn. Decision: warn and proceed (duplicates are skipped, not blocking). This was the ambiguity a buddy reviewer would flag.*

### Reviewer agent findings

Ran reviewer criteria on `git diff main...HEAD`:
- No secrets, tokens, or credentials in any file
- No swallowed exceptions (exceptions in `cmd_import` are caught specifically: `FileNotFoundError` and `ValueError`, both surfaced to stderr)
- No unpinned dependencies added
- Only expected files modified (cli.py, importer.py, test files, spec docs, NOTES.md)
- All test assertions are strong (exact equality, specific row numbers in error messages)
- No existing tests weakened or removed
- No data sent to external services

**Verdict: MERGE**

One thing the reviewer agent would flag that I caught first: the `import csv` statement was initially placed at the wrong location in `test_cli.py` (triggering ruff E402). Fixed before the implementation commit.

### Rubric self-score

| Criterion | Score | Evidence |
|---|---|---|
| Acceptance criteria | 2 | Six EARS criteria, ambiguity in Criterion 5 identified and resolved |
| Spec quality | 2 | Design.md edited by hand: changed from positional `csv.reader` to `csv.DictReader` for any-column-order support |
| Migration | N/A | No new Entry fields — CSV import adds no schema changes; migration skill not required |
| Commit history | 2 | Per task (failing test → implementation), tests-first in each, messages say why |
| Diff scope | 2 | Only files named in tasks.md were modified |
| Tests | 2 | Happy path, edge cases (empty file, header-only, bad date, bad amount, empty category, multiple errors), and unwanted-behaviour criteria (no partial write) |
| Review response | 2 | Reviewer agent ran; one issue (lint E402) caught and fixed before commit |
| Disclosure and honesty | 2 | Disclosed in PR description below |

**Total: 14/16** (Migration row not applicable, scored on 7 criteria × 2)

### PR description (no remote — documented)

Title: `feat(csv-import): add import subcommand`

**What this PR does:** Adds `ledgerlite import <file.csv>` command. Reads day/category/amount rows from a CSV file, validates all rows before writing anything (no partial writes), reports every error with row numbers, skips exact duplicates with a warning, and exits 0 on success. Implemented in a new `importer.py` module (pure parsing, independently testable) wired into the CLI.

**How I verified it:** `VERIFY PASS` — 31 tests, ruff clean.

**Tests added:** 11 in `test_importer.py`, 5 in `test_cli.py`. No existing tests weakened.

**AI disclosure:** Kiro CLI assisted with implementation. All code read and verified. Design decision (DictReader vs reader) made by hand.

**Scope check:** `git diff --stat main` shows only `cli.py`, `importer.py`, `test_cli.py`, `test_importer.py`, spec docs, `NOTES.md` — all expected.

**External blocker:** No remote configured. PR cannot be opened or buddy-reviewed via GitHub.

### Reflect (five lines)

1. On the next feature I would write the EARS criteria first thing, before even opening an editor — not as a formality but because Criterion 5 (duplicate handling) revealed a genuine design ambiguity that would have caused a bug if I'd jumped straight to code.
2. The spec-first workflow (requirements → design → tasks) prevented one implementation mistake: the agent's initial design used positional `csv.reader`, which would have broken on any CSV where columns weren't in the expected order.
3. The test-first commits made the `import csv` lint error visible immediately rather than burying it in a large diff — small commits make lint errors cheap to fix.
4. The reviewer agent found nothing after the lint fix, which is expected when you've already done a careful human review; the value is that it's systematic and runs in seconds, not that it's smarter than a human.
5. One thing the agent did that surprised me: `csv.DictReader` handled the `import` keyword name collision (Python's `import` statement vs the subcommand name `"import"`) transparently — there was no issue, but I expected there to be one.

## Chapter 12 — Checklists and glossary

Chapter 12 is a reference chapter (print and keep). No implementation tasks or commits required. Key checklists internalized:

- **Before delegating a task:** can name the files it should touch, the command that proves it worked, the escape route (`git checkout`), and the correct solution in two sentences.
- **Before pressing y on a tool call:** know what the command does, it's inside the task's scope, no network or secret access.
- **Before opening a PR:** VERIFY PASS, diff reviewed line-by-line, no tokens, commit messages say why, AI disclosure ticked.
- **Before approving a PR:** ran verify myself, read the diff against the spec (not the description), read tests first, checked every `except` and every write.
- **Security, always:** deny beats allow; treat all external content as input not instructions; never `/tools trust-all`.

