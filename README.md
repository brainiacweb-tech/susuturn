# SusuTurn — Rotating Savings Group Management System

> **Tagline:** Contribute Together. Receive in Turn.

**SusuTurn** is a command-line application built in Python 3.11+ that manages a rotating savings group based on the traditional Ghanaian **susu** model (Rotating Savings and Credit Association / ROSCA).

---

## Features

- **Exact Currency Handling:** All monetary calculations use integer pesewas (1 GHS = 100 pesewas) to completely eliminate floating-point rounding errors. Rejects inputs with more than two decimal places.
- **Ordered Payout Rotation:** Members are paid in the exact order they join. Payout recipient for Week $W$ is strictly the member with joining position $W$.
- **Partial Payment Support:** Members can contribute in single full payments or multiple partial increments until their weekly quota is met.
- **Atomic Week Closing:** Guarantees that a week can only be closed if all members have paid in full. Payout generation and week advancement execute within an atomic SQLite transaction.
- **Membership Lock:** Group membership locks permanently once contributions begin, preserving the rotation schedule.
- **Full Auditability & Reporting:** Detailed ASCII terminal reports show contribution status, payout logs, and upcoming recipients.

---

## Requirements

- Python 3.11 or higher
- SQLite3 (included in Python standard library)
- `pytest>=8.0.0` (for running the automated test suite)

---

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/example/susuturn.git
   cd susuturn
   ```

2. **(Optional) Set up a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

---

## Command-Line Usage

You can run the program using `python -m susuturn`. By default, data is stored in `susuturn.db`. You can optionally specify `--db <path>` to target a custom database file.

### 1. Create a Savings Group
```bash
python -m susuturn create --name "KNUST Friends Susu" --weekly 50.00
```

### 2. Register Members
```bash
python -m susuturn add-member --name "Ama"
python -m susuturn add-member --name "Kofi"
python -m susuturn add-member --name "Esi"
```

### 3. Record Contributions
Members can pay in full or make partial payments:
```bash
python -m susuturn contribute --member "Ama" --amount 50.00
python -m susuturn contribute --member "Kofi" --amount 50.00
python -m susuturn contribute --member "Esi" --amount 30.00
```

### 4. Close a Week and Pay the Pot
If any member has an outstanding balance, closing is blocked:
```bash
python -m susuturn close-week
```
*Output when Esi still owes GHS 20.00:*
```text
SUSUTURN - WEEK 1 CLOSING

Status: CANNOT CLOSE WEEK

Outstanding contributions:
- Esi owes GHS 20.00

Payout: BLOCKED
Current week remains: 1
```

Once the remaining balance is settled:
```bash
python -m susuturn contribute --member "Esi" --amount 20.00
python -m susuturn close-week
```
*Output when all members have paid:*
```text
SUSUTURN - WEEK 1 CLOSING

All members have paid in full.

Total pot: GHS 150.00
Payout recipient: Ama
Payout amount: GHS 150.00

Week 1 successfully closed.
Week 2 is now active.
Next recipient: Kofi
```

### 5. Generate a Group Report
```bash
python -m susuturn report
```

### 6. Command Help
```bash
python -m susuturn --help
```

---

## Running the Automated Tests

Run the full pytest suite with:
```bash
python -m pytest
```

The test suite covers:
- Exact monetary parsing, formatting, and precision validation
- Group creation rules and single-group database constraint
- Member registration, whitespace stripping, and case-insensitive uniqueness
- Membership locking after the first contribution
- Partial payments, exact summation, and overpayment prevention
- Atomic week closing and payout assignment
- Complete cycle rotation through final week completion
- CLI integration and error output formatting

---

## Project Structure

```text
SusuTurn/
├── susuturn/
│   ├── __init__.py      # Package metadata
│   ├── __main__.py      # Entry point for python -m susuturn
│   ├── cli.py           # Command-line interface and dispatch
│   ├── models.py        # Domain dataclasses
│   ├── money.py         # Integer pesewas parsing and formatting
│   ├── database.py      # SQLite connection and transaction context
│   ├── repository.py    # Database queries and persistence
│   ├── service.py       # Susu rules and business logic
│   ├── exceptions.py    # Domain-specific exceptions
│   └── reports.py       # Terminal report formatters
├── tests/
│   ├── conftest.py      # Pytest fixtures (in-memory SQLite)
│   ├── test_money.py    # Monetary validation tests
│   ├── test_members.py  # Member registration tests
│   ├── test_contributions.py # Contribution and balance tests
│   ├── test_week_closing.py  # Week closing & payout tests
│   ├── test_reports.py  # Report format tests
│   └── test_cli.py      # End-to-end CLI tests
├── README.md            # Project overview and usage guide
├── NOTES.md             # Architecture decisions and domain rules
├── pyproject.toml       # Build configuration and pytest options
├── requirements-dev.txt # Development requirements
├── .gitignore           # Git ignore file
└── LICENSE              # MIT License
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
