from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import report, store
from .importer import parse_csv
from .models import Entry

DEFAULT_LEDGER = Path("ledger.json")


def _validate_add(category: str, amount: str) -> tuple[str, int] | None:
    """Return (error message, exit code) if invalid, else None."""
    if not category.strip():
        return ("error: category is required", 2)
    try:
        value = Decimal(amount)
        if not value.is_finite() or value <= 0:
            return ("error: amount must be positive", 2)
    except Exception:
        return ("error: amount must be positive", 2)
    return None


def cmd_add(args: argparse.Namespace) -> int:
    problem = _validate_add(args.category, args.amount)
    if problem:
        msg, code = problem
        print(msg, file=sys.stderr)
        return code
    entries = store.load(args.ledger)
    day = date.fromisoformat(args.day)
    entry = Entry(day=day, category=args.category, amount=Decimal(args.amount))
    entries.append(entry)
    store.save(args.ledger, entries)
    print(f"added {args.category} {args.amount} on {args.day}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = sorted(store.load(args.ledger), key=lambda e: e.day)
    if args.last:
        entries = entries[-args.last :]
    for e in entries:
        print(f"{e.day.isoformat()}  {e.category:<16}{e.amount:>12.2f}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    entries = store.load(args.ledger)
    month_entries = report.entries_in_month(entries, args.year, args.month)
    print(report.format_report(args.year, args.month, report.totals_by_category(month_entries)))
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Import entries from a CSV file (day,category,amount). Validates all rows before writing."""
    csv_path = args.csvfile

    # Parse and validate
    try:
        new_entries, errors = parse_csv(csv_path)
    except FileNotFoundError:
        print(f"error: file not found: {csv_path}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 2

    # Deduplicate against existing ledger entries
    existing = store.load(args.ledger)
    existing_set = {(e.day, e.category, e.amount) for e in existing}

    to_add = []
    for entry in new_entries:
        key = (entry.day, entry.category, entry.amount)
        if key in existing_set:
            print(
                f"warning: skipping duplicate entry {entry.day} {entry.category} {entry.amount}",
                file=sys.stderr,
            )
        else:
            to_add.append(entry)

    store.save(args.ledger, existing + to_add)
    print(f"imported {len(to_add)} entries")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ledgerlite", description="Tiny expense ledger.")
    p.add_argument(
        "--ledger", type=Path, default=DEFAULT_LEDGER, help="ledger file (default: ledger.json)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="add an entry")
    a.add_argument("--day", default=date.today().isoformat())
    a.add_argument("--category", required=True)
    a.add_argument("--amount", required=True)
    a.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="list entries")
    ls.add_argument("--last", type=int, default=0, help="show only the last N entries")
    ls.set_defaults(func=cmd_list)

    r = sub.add_parser("report", help="monthly totals by category")
    r.add_argument("--year", type=int, required=True)
    r.add_argument("--month", type=int, required=True)
    r.set_defaults(func=cmd_report)

    imp = sub.add_parser("import", help="import entries from a CSV file")
    imp.add_argument("csvfile", type=Path, help="CSV file with day,category,amount columns")
    imp.set_defaults(func=cmd_import)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
