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
    assert lines and lines[0].startswith("2026-04-0")


def test_report_command(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    main([
        "--ledger", str(ledger), "add", "--day", "2026-04-02", "--category", "f", "--amount", "1"
    ])
    capsys.readouterr()
    assert main(["--ledger", str(ledger), "report", "--year", "2026", "--month", "4"]) == 0
    assert "TOTAL" in capsys.readouterr().out
