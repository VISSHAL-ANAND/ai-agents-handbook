from decimal import Decimal

from ledgerlite.cli import main


def test_add_then_list(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    args = ["--ledger", str(ledger), "add", "--day", "2026-04-02"]
    args += ["--category", "food", "--amount", "99.90"]
    assert main(args) == 0
    assert main(["--ledger", str(ledger), "list"]) == 0
    out = capsys.readouterr().out
    assert "2026-04-02" in out and "food" in out and "99.90" in out


def test_list_last_n(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    for d in ("2026-04-01", "2026-04-02", "2026-04-03"):
        main(["--ledger", str(ledger), "add", "--day", d, "--category", "c", "--amount", "1"])
    capsys.readouterr()
    main(["--ledger", str(ledger), "list", "--last", "2"])
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 2 and lines[0].startswith("2026-04-02")


def test_report_command(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    main([
        "--ledger", str(ledger), "add", "--day", "2026-04-02", "--category", "f", "--amount", "1"
    ])
    capsys.readouterr()
    assert main(["--ledger", str(ledger), "report", "--year", "2026", "--month", "4"]) == 0
    assert "TOTAL" in capsys.readouterr().out


# --- Task 2: budget set tests ---

def test_budget_set_persists(tmp_path, capsys):
    from ledgerlite import store

    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "budget", "set", "food", "5000"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "budget food set to 5000" in out
    budgets = store.load_budgets(ledger)
    assert budgets["food"] == 5000


def test_budget_set_overwrites(tmp_path, capsys):
    from ledgerlite import store

    ledger = tmp_path / "l.json"
    main(["--ledger", str(ledger), "budget", "set", "food", "5000"])
    capsys.readouterr()
    main(["--ledger", str(ledger), "budget", "set", "food", "3000"])
    capsys.readouterr()
    assert store.load_budgets(ledger)["food"] == Decimal("3000")


def test_budget_set_zero_amount(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "budget", "set", "food", "0"])
    assert rc == 2
    assert "amount must be positive" in capsys.readouterr().err
    assert not ledger.exists()


def test_budget_set_negative_amount(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "budget", "set", "food", "-100"])
    assert rc == 2
    assert "amount must be positive" in capsys.readouterr().err
    assert not ledger.exists()


def test_budget_set_invalid_amount(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "budget", "set", "food", "abc"])
    assert rc == 2
    assert "amount must be positive" in capsys.readouterr().err
    assert not ledger.exists()


def test_budget_set_empty_category(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "budget", "set", "   ", "5000"])
    assert rc == 2
    assert "category is required" in capsys.readouterr().err
    assert not ledger.exists()
