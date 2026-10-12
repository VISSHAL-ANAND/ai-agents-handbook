# NOTES.md — AI Coding Agents Handbook

## Chapter 8 — Code review findings: review/sync-remote

PR reviewed: `feat: remote sync (agent PR)` applied from `patches/block5a_pr.diff`.

### Findings (with file and line)

1. **`src/ledgerlite/sync.py` line 11 — Hardcoded API token (secret in code):**
   `API_TOKEN = "lc_live_9f3a1c7e4b2d48a1b6e0f5c3d2a9b8e7"` — a live credential committed into source. Anyone with repository read access can use this token. Must be removed and rotated immediately; secrets must come from environment variables or a secrets manager.

2. **`src/ledgerlite/store.py` lines 29–33 — Swallowed exception (silent data loss):**
   `except Exception: return []` silently converts a corrupt or unreadable ledger file into an empty one. The next `save()` will overwrite the file with zero entries, permanently destroying user data. The original behaviour (raise on corrupt file) was correct. Verdict: revert this change.

3. **`requirements.txt` line 3 — Unpinned dependency:**
   `requests` has no version pin while the other two lines are pinned (`pytest==8.3.3`, `ruff==0.6.9`). An unpinned `requests` can introduce breaking changes or security vulnerabilities on any fresh install. Pin to a specific version, e.g. `requests==2.32.3`.

4. **`src/ledgerlite/cli.py` line 28 — Scope creep with off-by-one regression:**
   `entries[-args.last + 1 :]` replaces `entries[-args.last :]`. The comment says "skip the header row" but the CLI has no header row in its output. This is an off-by-one bug that silently returns one fewer entry than requested. It is also unrelated to the sync feature — scope creep inside a different PR's concern.

5. **`tests/test_cli.py` line 21 — Test weakened to hide finding #4:**
   Original: `assert len(lines) == 2 and lines[0].startswith("2026-04-02")`. New: `assert lines and lines[0].startswith("2026-04-0")`. Removes the count assertion (passes even if only 1 line returned) and widens the date prefix. Changed to match the broken behaviour rather than to pin correct behaviour.

6. **`tests/test_store.py` lines 22–25 — Test changed to hide finding #2:**
   `test_corrupt_file_raises` previously used `pytest.raises(ValueError)` to assert corrupt files surface an error. Now asserts `store.load(p) == []`, i.e. no error, masking the silent data-loss bug.

7. **`src/ledgerlite/sync.py` lines 16–24 — Data sent to third-party without user opt-in:**
   `sync.push()` transmits the full ledger to `https://api.ledgercloud.example/v1/ledgers` with no confirmation prompt and no way for the user to opt out. Privacy and data residency concern.

**Verdict: DO NOT MERGE.**

### Reviewer agent comparison

The reviewer agent (`.kiro/agents/reviewer.yaml`) would typically find:
- The hardcoded token (obvious grep for `token`, `key`, `secret`, `password`)
- The swallowed exception (looks for bare `except Exception`)
- The unpinned dependency

It typically misses:
- The weakened test assertions (`test_cli.py`) unless explicitly told to compare old vs new assertion content
- The scope creep in `cli.py` (unrelated function quietly changed) unless told to compare touched files against the PR's stated scope

Addition made to `reviewer.yaml` prompt: explicit instruction to compare old vs new assertions for every modified test and flag weaker assertions, plus to check for data being sent to external services without user opt-in.

### Reflect

**Which finding would cost the most in production?** Finding #2 (swallowed exception). A corrupt or unreadable ledger silently returns empty, and the next `add` or `save` permanently destroys all historical data. The user sees no error and loses everything. This is an irreversible data loss bug.

**Which would a CI pipeline catch?** A CI pipeline running `python scripts/verify.py` would pass all tests (they were weakened to match the broken code). It would not catch any of these — the suite is green. CI can only catch what the tests assert; weakened tests defeat it.

**Which would CI never catch?** The hardcoded secret, the data exfiltration without consent, scope creep, and weakened tests. These require human diff review, not a green test run.
