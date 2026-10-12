# AGENTS.md

This is the portable instruction file for any coding agent that opens this repo. Kiro loads it through `.kiro/steering/project.md`. Chapter 4 of the handbook asks you to complete the TODO sections. Every line must be true and checkable.

## What this is
`ledgerlite` is a tiny personal expense ledger: a Python library in `src/ledgerlite/` and a CLI (`ledgerlite add | list | report`). Entries live in a JSON file with a schema version. Amounts are `Decimal`, never `float`.

## Commands
- Install: `python -m pip install -e ".[dev]"`
- Verify (lint plus tests, the only gate that matters): `python scripts/verify.py`
- Run: `python -m ledgerlite.cli --ledger demo.json add --category food --amount 120.50`

## Conventions
- Code lives in `src/ledgerlite/`; tests live in `tests/`.
- All test files are named `test_*.py` and use pytest.
- Formatter and linter: Ruff, line length 100. Must pass before commit.
- Money values are always `Decimal`, never `float`.
- Function and variable names use `snake_case`; classes use `PascalCase`.
- Commit messages follow Conventional Commits: `type(scope): description` (e.g. `feat(cli): add export command`).

## Definition of done
- `python scripts/verify.py` prints `VERIFY PASS` (lint + all tests pass).
- Every new behaviour has at least one new test covering it.
- The diff touches only files within the scope of the task; no unrelated files changed.
- When reporting completion, state: files changed, tests added, verify result.

## Never do
- Never make network calls from this repo; there is no reason for one.
- Never add, remove, or rename a field on `Entry` or change the JSON layout without following the `ledgerlite-migration` skill in `.kiro/skills/`.
- Never delete or weaken an existing test (do not remove assertions, lower thresholds, or mark tests as skipped).
- Never run `git push` or any destructive git operation (`--force`, `reset --hard`, `branch -D`, `clean -f`); stop and ask first.
- Never modify files under `.kiro/` without explicitly asking the user first.

## Schema changes
Any change to `Entry` fields or the JSON layout must follow the `ledgerlite-migration` skill in `.kiro/skills/`.
