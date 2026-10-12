# NOTES.md — AI Coding Agents Handbook

## Chapter 6 — Reflect

Root cause identified: in `src/ledgerlite/report.py` line 11, `month_range` computes the last day by constructing `date(year, month + 1, 1)`. When `month=12`, `month + 1 = 13` is out of range and Python raises `ValueError: month must be in 1..12`. The agent identified the root cause precisely on the first ask — it pointed to the exact line and explained that `month + 1` overflows the valid month range for December. The fix was a single conditional: when `month == 12`, use `date(year + 1, 1, 1) - timedelta(days=1)` instead.

Under "must stay unchanged": `entries_in_month`, `totals_by_category`, `format_report`, all existing tests (none could be weakened), and the public signature of `month_range` itself. These were the constraints that kept the fix minimal and correct.

**PR:** `fix: report crashes for December (#131)` — three commits in order: failing test → fix → characterization. No remote exists in this repo; the PR would be opened on GitHub after pushing the branch.

## Chapter 7 — Git and pull requests

**One-time local setup completed:**
- `git config --global pull.rebase false` — set (was unset).
- `git config --global user.name` / `user.email` — already configured.

**Branches ready for PR:**
- `ch3-directed` — 3 commits ahead of main: `feat(cli): reject non-positive amounts`, reflection, agent instructions.
- `ch4-with-skill` — 3 commits ahead of main: `feat: add currency field with schema migration`, reflection, acceptance criteria.

**External blocker:** No Git remote is configured for this repository. The chapter's Do exercise requires pushing both branches to GitHub, opening PRs with the template filled, and receiving a buddy review comment. This cannot be completed locally. All locally-possible work is done: git config set, branches exist with correct history, PR template understood.

**PR descriptions that would be submitted (not opened — no remote):**

PR 1 — ch3-directed: `feat(cli): reject non-positive amounts` — adds validation to add command rejecting empty categories and non-positive amounts. VERIFY PASS, tests added, AI disclosure ticked.

PR 2 — ch4-with-skill: `feat: add currency field with schema migration` — adds currency field to Entry following the ledgerlite-migration skill; bumps schema version, registers migration, adds fixture. VERIFY PASS, AI disclosure ticked.

**Reflect:** VERIFY PASS cannot catch intent drift (agent adding unrelated changes), hardcoded test-environment values, or weakened assertions where the test still passes but asserts less. A buddy reviewer catches these by reading the diff against the spec. The key gap is that green tests only prove what was tested, not that nothing else changed unintentionally.
