from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from . import report, store
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
    # Over-budget warning (advisory — entry is already saved, exit code stays 0)
    budgets = store.load_budgets(args.ledger)
    if args.category in budgets:
        month_entries = report.entries_in_month(entries, day.year, day.month)
        totals = report.totals_by_category(month_entries)
        if totals.get(args.category, Decimal("0")) > budgets[args.category]:
            print(
                f"warning: {args.category} over budget for {day.year}-{day.month:02d}",
                file=sys.stderr,
            )
    return 0


def cmd_budget_set(args: argparse.Namespace) -> int:
    problem = _validate_add(args.category, args.amount)
    if problem:
        msg, code = problem
        print(msg, file=sys.stderr)
        return code
    budgets = store.load_budgets(args.ledger)
    budgets[args.category] = Decimal(args.amount)
    store.save_budgets(args.ledger, budgets)
    print(f"budget {args.category} set to {args.amount}")
    return 0


def _month_last_day(year: int, month: int) -> date:
    """Last calendar day of any month, including December."""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def cmd_budget_status(args: argparse.Namespace) -> int:
    try:
        first = date(args.year, args.month, 1)
        last = _month_last_day(args.year, args.month)
    except ValueError:
        print("error: invalid year/month", file=sys.stderr)
        return 2

    budgets = store.load_budgets(args.ledger)
    if not budgets:
        print("no budgets set")
        return 0

    entries = store.load(args.ledger)
    month_entries = [e for e in entries if first <= e.day <= last]
    totals = report.totals_by_category(month_entries)

    for category in sorted(budgets):
        budget_amt = budgets[category]
        spent = totals.get(category, Decimal("0"))
        remaining = budget_amt - spent
        print(
            f"{category:<16}"
            f"  budget: {budget_amt:>10.2f}"
            f"  spent: {spent:>10.2f}"
            f"  remaining: {remaining:>10.2f}"
        )
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

    b = sub.add_parser("budget", help="manage category budgets")
    bsub = b.add_subparsers(dest="budget_command", required=True)

    bs = bsub.add_parser("set", help="set a category budget")
    bs.add_argument("category")
    bs.add_argument("amount")
    bs.set_defaults(func=cmd_budget_set)

    bst = bsub.add_parser("status", help="show budget vs. spend for a month")
    bst.add_argument("--year", type=int, required=True)
    bst.add_argument("--month", type=int, required=True)
    bst.set_defaults(func=cmd_budget_status)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
