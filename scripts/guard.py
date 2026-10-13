"""PreToolUse guard for shell commands. Chapter 9 of the handbook.

Kiro sends the pending tool call as JSON on stdin. This script:
1. appends the raw event to guard-audit.log (gitignored) so you can see what the agent tried
2. exits 2 with a reason on stderr when the command contains a blocked pattern

Exit code 2 is the block signal for PreToolUse hooks. If your Kiro version behaves
differently, ask:  /guide how does a PreToolUse command hook block a tool call?
"""

import json
import pathlib
import sys

BLOCK = (
    "curl",
    "wget",
    "nc ",
    "Invoke-WebRequest",
    "Invoke-RestMethod",
    "ATTACKER",
    ".kiro/settings",
    "permissions.yaml",
    "git push --force",
    "git push -f",
    # Chapter 9 Part C additions
    "base64",
    "$HOME/.kiro",
)

MAX_COMMAND_LENGTH = 400  # obfuscation tell: very long commands are suspicious

LOG = pathlib.Path(__file__).resolve().parent.parent / "guard-audit.log"


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = {"raw": raw}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event)[:2000] + "\n")
    text = json.dumps(event)

    # Check for blocked keyword patterns
    hit = next((b for b in BLOCK if b in text), None)
    if hit:
        print(f"guard.py blocked this command: it contains '{hit}'. Ask the user instead.", file=sys.stderr)
        return 2

    # Check for suspiciously long commands (common obfuscation technique)
    command = event.get("command", "") if isinstance(event, dict) else ""
    if len(command) > MAX_COMMAND_LENGTH:
        reason = f"command length {len(command)} exceeds limit {MAX_COMMAND_LENGTH} (obfuscation check)"
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"blocked": reason, "command_prefix": command[:80]}) + "\n")
        print(f"guard.py blocked this command: {reason}. Ask the user instead.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
