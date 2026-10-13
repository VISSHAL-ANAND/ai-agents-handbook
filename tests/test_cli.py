import csv

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


def _write_csv(tmp_path, rows, fieldnames=None):
    p = tmp_path / "import.csv"
    if fieldnames is None:
        fieldnames = ["day", "category", "amount"]
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return p


def test_import_valid_csv(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    p = _write_csv(tmp_path, [
        {"day": "2024-03-01", "category": "food", "amount": "100"},
        {"day": "2024-03-02", "category": "rent", "amount": "5000"},
    ])
    rc = main(["--ledger", str(ledger), "import", str(p)])
    out, err = capsys.readouterr()
    assert rc == 0
    assert "imported 2 entries" in out
    assert err == ""
    # entries are in the ledger
    from ledgerlite import store
    entries = store.load(ledger)
    assert len(entries) == 2


def test_import_file_not_found(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    rc = main(["--ledger", str(ledger), "import", str(tmp_path / "missing.csv")])
    out, err = capsys.readouterr()
    assert rc == 2
    assert "not found" in err.lower()
    assert out == ""
    # ledger untouched
    assert not ledger.exists()


def test_import_invalid_rows_no_partial_write(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    p = _write_csv(tmp_path, [
        {"day": "2024-03-01", "category": "food", "amount": "100"},
        {"day": "bad-date", "category": "food", "amount": "50"},
        {"day": "2024-03-03", "category": "", "amount": "20"},
    ])
    rc = main(["--ledger", str(ledger), "import", str(p)])
    out, err = capsys.readouterr()
    assert rc == 2
    assert out == ""
    assert "row 2" in err
    assert "row 3" in err
    # nothing written
    assert not ledger.exists()


def test_import_empty_csv(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    p = tmp_path / "empty.csv"
    p.write_text("day,category,amount\n", encoding="utf-8")
    rc = main(["--ledger", str(ledger), "import", str(p)])
    out, err = capsys.readouterr()
    assert rc == 2
    assert "no data rows" in err.lower()


def test_import_duplicate_skipped(tmp_path, capsys):
    ledger = tmp_path / "l.json"
    # pre-load one entry
    main(["--ledger", str(ledger), "add", "--day", "2024-03-01",
          "--category", "food", "--amount", "100"])
    capsys.readouterr()
    # CSV has that same entry + one new one
    p = _write_csv(tmp_path, [
        {"day": "2024-03-01", "category": "food", "amount": "100"},
        {"day": "2024-03-05", "category": "transport", "amount": "40"},
    ])
    rc = main(["--ledger", str(ledger), "import", str(p)])
    out, err = capsys.readouterr()
    assert rc == 0
    assert "imported 1 entries" in out
    assert "duplicate" in err.lower() or "skip" in err.lower()
    from ledgerlite import store
    entries = store.load(ledger)
    assert len(entries) == 2  # original + 1 new, not 3
