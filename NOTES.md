# NOTES.md — AI Coding Agents Handbook

## Chapter 11 — Capstone: CSV import

### Feature: CSV import

`import file.csv` reads `day,category,amount` rows, validates every row, reports all errors before writing anything, and writes only if all rows are valid.

### Six EARS acceptance criteria

**Criterion 1 — Ubiquitous (input format)**
The system shall accept a CSV file with a header row containing exactly the columns `day`, `category`, and `amount` in any order; rows that do not conform to this format are treated as validation errors.

**Criterion 2 — Event-driven (successful import)**
WHEN the user runs `import <file.csv>` and all rows are valid, the system shall append the new entries to the ledger file, print `imported N entries` to stdout, and exit with code 0.

**Criterion 3 — Unwanted (any row invalid — no partial write)**
IF any row in the CSV file fails validation (non-positive or non-numeric amount, empty category, invalid date format, or missing required column), THEN the system shall print every error to stderr with the row number, write nothing to the ledger file, and exit with code 2.

**Criterion 4 — Unwanted (file not found)**
IF the CSV file path does not exist, THEN the system shall print `error: file not found: <path>` to stderr and exit with code 2 without modifying the ledger.

**Criterion 5 — State-driven (idempotency guard)**
WHILE the CSV file contains a row whose `day`, `category`, and `amount` exactly match an entry already in the ledger, the system shall report a warning for that row but still write the remaining unique entries and exit with code 0.
*(Open for design phase: whether duplicate detection is exact-match only or approximate.)*

**Criterion 6 — Unwanted (empty file or header-only)**
IF the CSV file is empty or contains only a header row with no data rows, THEN the system shall print `error: no data rows in <path>` to stderr and exit with code 2.

*Ambiguity noted and resolved before implementation: Criterion 5 (duplicate handling) initially said "report a warning" without specifying whether duplicates block the import or just warn. Decision: warn and proceed (duplicates are skipped, not blocking). This was the ambiguity a buddy reviewer would flag.*
