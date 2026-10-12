from __future__ import annotations

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from .models import Entry

SCHEMA_VERSION = 2

# Maps a schema version to the function that upgrades a raw file dict to the next version.
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def _migrate_v1_to_v2(data: dict) -> dict:
    """Add budgets key (empty dict) to files that lack it."""
    if "budgets" not in data:
        data["budgets"] = {}
    return data


MIGRATIONS[1] = _migrate_v1_to_v2


def _migrate(data: dict) -> dict:
    version = data.get("schema_version", 1)
    while version < SCHEMA_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["schema_version"] = version
    return data


def load(path: Path) -> list[Entry]:
    """Load entries. A missing file is an empty ledger. A corrupt file is an error."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    data = _migrate(data)
    return [Entry.from_dict(d) for d in data["entries"]]


def save(path: Path, entries: list[Entry]) -> None:
    """Save entries, preserving budgets already on disk.

    If the file exists but cannot be parsed, raises rather than silently
    overwriting a ledger that may contain budget data we cannot read.
    """
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


def load_budgets(path: Path) -> dict[str, Decimal]:
    """Return the budgets dict. Missing file or missing key returns empty dict."""
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
