# NOTES.md — AI Coding Agents Handbook

## Chapter 6 — Reflect

Root cause identified: in `src/ledgerlite/report.py` line 11, `month_range` computes the last day by constructing `date(year, month + 1, 1)`. When `month=12`, `month + 1 = 13` is out of range and Python raises `ValueError: month must be in 1..12`. The agent identified the root cause precisely on the first ask — it pointed to the exact line and explained that `month + 1` overflows the valid month range for December. The fix was a single conditional: when `month == 12`, use `date(year + 1, 1, 1) - timedelta(days=1)` instead.

Under "must stay unchanged": `entries_in_month`, `totals_by_category`, `format_report`, all existing tests (none could be weakened), and the public signature of `month_range` itself. These were the constraints that kept the fix minimal and correct.

**PR:** `fix: report crashes for December (#131)` — three commits in order: failing test → fix → characterization. No remote exists in this repo; the PR would be opened on GitHub after pushing the branch.
