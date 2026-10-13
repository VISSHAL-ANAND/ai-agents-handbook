from __future__ import annotations

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from .models import Entry

SCHEMA_VERSION = 3

MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def _migrate_v1_to_v2(data: dict) -> dict:
    """Add the default INR currency to entries that lack it."""
    for entry in data.get("entries", []):
        if "currency" not in entry:
            entry["currency"] = "INR"
    return data


def _migrate_v2_to_v3(data: dict) -> dict:
    """Add an empty budgets mapping when one is missing."""
    if "budgets" not in data:
        data["budgets"] = {}
    return data


MIGRATIONS[1] = _migrate_v1_to_v2
MIGRATIONS[2] = _migrate_v2_to_v3


def _migrate(data: dict) -> dict:
    version = data.get("schema_version", 1)
    if not isinstance(version, int) or version < 1 or version > SCHEMA_VERSION:
        raise ValueError(f"Unsupported ledger schema version: {version}")
    while version < SCHEMA_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["schema_version"] = version
    return data


def load(path: Path) -> list[Entry]:
    """Load entries. A missing file is an empty ledger; corrupt files raise."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    data = _migrate(data)
    return [Entry.from_dict(entry) for entry in data["entries"]]


def save(path: Path, entries: list[Entry]) -> None:
    """Save entries while preserving existing budgets."""
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        existing = _migrate(existing)
        budgets = existing.get("budgets", {})
    else:
        budgets = {}

    payload = {
        "schema_version": SCHEMA_VERSION,
        "entries": [entry.to_dict() for entry in entries],
        "budgets": budgets,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_budgets(path: Path) -> dict[str, Decimal]:
    """Return budgets; missing files or keys produce an empty mapping."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    data = _migrate(data)
    return {key: Decimal(value) for key, value in data.get("budgets", {}).items()}


def save_budgets(path: Path, budgets: dict[str, Decimal]) -> None:
    """Save budgets while preserving entries and the current schema."""
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data = _migrate(data)
    else:
        data = {"schema_version": SCHEMA_VERSION, "entries": []}

    data["budgets"] = {key: str(value) for key, value in budgets.items()}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)
