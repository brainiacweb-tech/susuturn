<div align="center">

# 🇬🇭 SusuTurn

### Professional Rotating Savings Group Management System
#### *Contribute Together. Receive in Turn.*

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-006B3F?logo=python&logoColor=white)](https://python.org)
[![CI Tests](https://github.com/brainiacweb-tech/susuturn/actions/workflows/tests.yml/badge.svg)](https://github.com/brainiacweb-tech/susuturn/actions)
[![Tests](https://img.shields.io/badge/tests-46%20passing-006B3F?logo=pytest&logoColor=white)](https://github.com/brainiacweb-tech/susuturn)
[![Database](https://img.shields.io/badge/database-SQLite%203-FCD116?logo=sqlite&logoColor=black)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-CE1126.svg)](https://github.com/brainiacweb-tech/susuturn/blob/main/LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-111111)](https://peps.python.org/pep-0008/)
[![Ghanaian Susu](https://img.shields.io/badge/model-Traditional%20Ghanaian%20ROSCA-006B3F)](https://en.wikipedia.org/wiki/Rotating_savings_and_credit_association)

**[📖 Plain Words](#-susuturn-in-plain-words)** ·
**[✨ Features](#-key-features)** ·
**[🚀 Quickstart](#-quickstart--usage-guide)** ·
**[🏗️ Architecture](#%EF%B8%8F-architecture--software-design)** ·
**[🧪 Testing](#-automated-testing)** ·
**[📜 Susu Rules](#-core-susu-rules--invariants)** ·
**[🤝 Contributing](#-contributing)**

</div>

---

> [!NOTE]
> **What is a Susu?**
> In Ghana and throughout West Africa, a **susu** is an informal Rotating Savings and Credit Association (ROSCA). A group of trusted people agree to save together: every member contributes the exact same amount each week, and every week the entire collected pot is paid out to one member in turn. When every person has taken their turn, the cycle is complete.

---

## 📖 SusuTurn in Plain Words

*No finance or software engineering background required.*

Imagine three friends in Kumasi—**Ama**, **Kofi**, and **Esi**—who want to save **GHS 50.00** each week:

```mermaid
flowchart LR
    A["Week 1: Ama, Kofi, Esi each contribute GHS 50"] --> P1["Ama receives pot: GHS 150.00"]
    P1 --> B["Week 2: Ama, Kofi, Esi each contribute GHS 50"]
    B --> P2["Kofi receives pot: GHS 150.00"]
    P2 --> C["Week 3: Ama, Kofi, Esi each contribute GHS 50"]
    C --> P3["Esi receives pot: GHS 150.00"]
    P3 --> FIN["Cycle Complete! 🎉"]

    style A fill:#e8f5e9,stroke:#006b3f,stroke-width:2px;
    style B fill:#e8f5e9,stroke:#006b3f,stroke-width:2px;
    style C fill:#e8f5e9,stroke:#006b3f,stroke-width:2px;
    style P1 fill:#fff8e1,stroke:#fcd116,stroke-width:2px;
    style P2 fill:#fff8e1,stroke:#fcd116,stroke-width:2px;
    style P3 fill:#fff8e1,stroke:#fcd116,stroke-width:2px;
    style FIN fill:#ffebee,stroke:#ce1126,stroke-width:2px;
```

### The Three Big Problems in Traditional Susu Groups
1. 💸 **Floating-point errors in computers:** Binary computer floats can turn `0.10 + 0.20` into `0.30000000000000004`. Over weeks, pots fail to balance.
2. 🦹 **Partial payment confusion:** When members pay in installments (e.g., GHS 20 today, GHS 30 tomorrow), paper notebooks get messy and errors occur.
3. 🏃 **Unfair payouts & defaults:** If a week closes before everyone pays, whoever takes the pot early gets free money while others are shortchanged.

**SusuTurn solves all three:**
- **Zero Float Loss:** Stores money in integer **pesewas** ($1\text{ GHS} = 100\text{ pesewas}$).
- **Exact Installment Tracking:** Supports multiple partial payments while preventing overpayments.
- **Strict Atomic Payout Gate:** If even 1 pesewa is outstanding, the payout is blocked, the week stays open, and debtors are clearly displayed.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🪙 **Integer Pesewa Precision** | Complete immunity to floating-point rounding errors. Rejects malformed values, negative inputs, and numbers with $>2$ decimal places. |
| 🛡️ **Atomic Payout Protection** | Payout generation and week advancement execute inside an atomic SQLite transaction. Either both succeed, or zero changes occur. |
| 🔒 **Membership Lock** | Automatically locks membership the instant the first contribution is made, preventing rotation sabotage. |
| 🔢 **Deterministic Turn Rotation** | The payout sequence is determined solely by permanent joining order ($1, 2, \dots, N$), never alphabetically or arbitrarily. |
| 💵 **Partial Payment Accounting** | Members can pay in full or in multiple partial installments. Overpayments above the remaining weekly balance are strictly rejected. |
| 📊 **Audit-Ready Reporting** | Clean, formatted terminal summaries showing active week metrics, debtor balances, complete payout histories, and upcoming turns. |
| 💾 **Isolated Database Cycles** | Each database file represents one immutable rotation cycle. Run multiple groups or successive years using `--db`. |

---

## 📋 Requirements

- **Python 3.11** or higher
- **SQLite 3** (included in Python standard library)
- **pytest >= 8.0.0** (for running automated tests)

---

## 🚀 Quickstart & Usage Guide

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/brainiacweb-tech/susuturn.git
cd susuturn

# Install development dependencies
pip install -r requirements-dev.txt
```

---

### 2. Walkthrough: Running a Complete 3-Week Cycle

#### Step 1: Create the Savings Group
```bash
python -m susuturn create --name "KNUST Friends Susu" --weekly 50.00
```
```text
Savings group 'KNUST Friends Susu' created successfully.
Weekly contribution: GHS 50.00
```

#### Step 2: Register Members (Joining Order = Payout Order)
```bash
python -m susuturn add-member --name "Ama"
python -m susuturn add-member --name "Kofi"
python -m susuturn add-member --name "Esi"
```
```text
Member 'Ama' registered successfully.
Joining Position: #1 (Payout Week: 1)
Member 'Kofi' registered successfully.
Joining Position: #2 (Payout Week: 2)
Member 'Esi' registered successfully.
Joining Position: #3 (Payout Week: 3)
```

#### Step 3: Record Contributions for Week 1
```bash
python -m susuturn contribute --member "Ama" --amount 50.00
python -m susuturn contribute --member "Kofi" --amount 50.00
python -m susuturn contribute --member "Esi" --amount 30.00
```
```text
Payment of GHS 30.00 recorded for Esi (Week 1).
Total contributed this week: GHS 30.00
Remaining balance: GHS 20.00
```

#### Step 4: Attempt to Close Week 1 (Blocked Safeguard)
```bash
python -m susuturn close-week
```
```text
SUSUTURN - WEEK 1 CLOSING

Status: CANNOT CLOSE WEEK

Outstanding contributions:
- Esi owes GHS 20.00

Payout: BLOCKED
Current week remains: 1
```

#### Step 5: Settle Balance & Pay Out Week 1
```bash
python -m susuturn contribute --member "Esi" --amount 20.00
python -m susuturn close-week
```
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

#### Step 6: Inspect Group Status Report
```bash
python -m susuturn report
```
```text
============================================================
                    SUSUTURN GROUP REPORT                   
============================================================

GROUP SUMMARY
-------------
Group Name:          KNUST Friends Susu
Weekly Contribution: GHS 50.00
Total Members:       3
Cycle Status:        ACTIVE
Current Week:        Week 2
Total Weekly Pot:    GHS 150.00

MEMBER CONTRIBUTION REPORT
--------------------------
Pos   Member Name          Contributed     Outstanding     Status    
---------------------------------------------------------------------
1     Ama                  GHS 0.00        GHS 50.00       OWING     
2     Kofi                 GHS 0.00        GHS 50.00       OWING     
3     Esi                  GHS 0.00        GHS 50.00       OWING     

PAYOUT HISTORY
--------------
Week   Recipient            Amount          Date (UTC)          
----------------------------------------------------------------
1      Ama                  GHS 150.00      2026-10-16 11:42:00 

UPCOMING PAYOUT
---------------
Next scheduled recipient: Kofi (Week 2)
============================================================
```

---

## 💻 CLI Reference

All commands support the `--db <path>` flag to specify a custom SQLite database file (default: `susuturn.db`).

| Command | Arguments | Description |
|---|---|---|
| `create` | `--name <STR>`, `--weekly <AMT>` | Initialize the single savings group |
| `add-member` | `--name <STR>` | Register a member in sequential order |
| `contribute` | `--member <STR>`, `--amount <AMT>` | Record a full or partial contribution |
| `close-week` | *(none)* | Verify debts, record payout, advance week |
| `report` | *(none)* | Display comprehensive ASCII audit report |
| `--help` | *(none)* | Display usage guidance and syntax |

---

## 🏗️ Architecture & Software Design

SusuTurn follows a modular layered architecture with strict separation of concerns:

```text
susuturn/
├── __init__.py      # Package metadata & version
├── __main__.py      # python -m susuturn execution entry point
├── cli.py           # argparse CLI parsing, exit codes & formatting
├── models.py        # Immutable dataclasses (Group, Member, Contribution, Payout)
├── money.py         # Integer pesewa validation, parser & currency formatter
├── database.py      # SQLite connection manager, foreign keys & transaction scope
├── repository.py    # SQL persistence & query operations
├── service.py       # Susu business rules, domain invariants & state transitions
├── exceptions.py    # Domain exception hierarchy
└── reports.py       # Clean ASCII table & report formatters
```

### Relational Schema Diagram

```mermaid
erDiagram
    SAVINGS_GROUPS ||--o{ MEMBERS : "contains"
    MEMBERS ||--o{ CONTRIBUTIONS : "records"
    MEMBERS ||--o{ PAYOUTS : "receives"

    SAVINGS_GROUPS {
        int id PK "Enforces CHECK(id = 1)"
        string name "Group title"
        int weekly_contribution_pesewas "Contribution in pesewas"
        string created_at "ISO-8601 UTC timestamp"
        int current_week "Active week number"
        int is_completed "0=active, 1=finished"
    }

    MEMBERS {
        int id PK "Autoincrement"
        string name "Display name"
        string normalized_name UK "Lowercase unique constraint"
        int joining_position UK "Sequential payout position"
        string created_at "ISO-8601 UTC timestamp"
    }

    CONTRIBUTIONS {
        int id PK "Autoincrement"
        int member_id FK "References members(id)"
        int week_number "Active week when paid"
        int amount_pesewas "Payment in pesewas"
        string created_at "ISO-8601 UTC timestamp"
    }

    PAYOUTS {
        int id PK "Autoincrement"
        int week_number UK "One payout per week"
        int recipient_member_id UK "One payout per member"
        int amount_pesewas "Total pot in pesewas"
        string created_at "ISO-8601 UTC timestamp"
    }
```

---

## 📜 Core Susu Rules & Invariants

1. **One Rotation Cycle per Database:**
   A database represents exactly one closed savings cycle. Once the final member receives their pot, the cycle is permanently marked `COMPLETED`. Starting another rotation requires a fresh database file (e.g. `susuturn --db cycle2.db create ...`).
2. **Permanent Payout Order:**
   The member registered at position $K$ receives their payout on Week $K$. Payout orders can never be altered or shuffled.
3. **Membership Lock Rule:**
   Membership permanently locks the moment the first contribution transaction is recorded. No members can be added, removed, or modified once money begins moving.
4. **No Double Payouts:**
   Database-level unique constraints on `payouts.recipient_member_id` guarantee that no member can ever receive the pot twice.
5. **No Overpayments:**
   Contributions cannot exceed a member's remaining balance for the active week.
6. **Atomic Closing:**
   Advancing the week and distributing the pot execute inside SQLite's `BEGIN IMMEDIATE` transaction.

---

## 🧪 Automated Testing

SusuTurn includes an extensive automated test suite with **46 tests** covering every functional edge case, monetary precision boundary, database constraint, single-member deadlock prevention, and multi-threaded race conditions. All tests are continuously verified on every commit across Python 3.11, 3.12, and 3.13 via GitHub Actions.

Run the test suite locally:
```bash
python -m pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\USER\OneDrive\Desktop\SusuTurn
configfile: pyproject.toml
testpaths: tests
collected 46 items

tests/test_cli.py::TestCLI::test_cli_help PASSED                         [  2%]
tests/test_cli.py::TestCLI::test_cli_no_args_shows_help PASSED           [  4%]
tests/test_cli.py::TestCLI::test_cli_lifecycle PASSED                    [  6%]
tests/test_cli.py::TestCLI::test_cli_duplicate_group_error PASSED        [  8%]
tests/test_cli.py::TestCLI::test_cli_invalid_money_error PASSED          [ 10%]
tests/test_contributions.py::TestContributions::test_record_single_full_contribution PASSED [ 13%]
tests/test_contributions.py::TestContributions::test_record_partial_contributions_and_exact_sum PASSED [ 15%]
tests/test_contributions.py::TestContributions::test_reject_unknown_member_contribution PASSED [ 17%]
tests/test_contributions.py::TestContributions::test_reject_zero_or_negative_contribution PASSED [ 19%]
tests/test_contributions.py::TestContributions::test_reject_payment_exceeding_remaining_balance PASSED [ 21%]
tests/test_contributions.py::TestContributions::test_reject_payment_when_already_fully_paid PASSED [ 23%]
tests/test_contributions.py::TestContributions::test_reject_contribution_with_single_member_and_membership_not_locked PASSED [ 26%]
tests/test_members.py::TestMembers::test_create_savings_group PASSED     [ 28%]
tests/test_members.py::TestMembers::test_reject_second_group_creation PASSED [ 30%]
tests/test_members.py::TestMembers::test_add_members_preserves_joining_order PASSED [ 32%]
tests/test_members.py::TestMembers::test_reject_blank_or_whitespace_name PASSED [ 34%]
tests/test_members.py::TestMembers::test_trim_surrounding_whitespace PASSED [ 36%]
tests/test_members.py::TestMembers::test_reject_duplicate_member_names_case_insensitive PASSED [ 39%]
tests/test_members.py::TestMembers::test_add_member_requires_group PASSED [ 41%]
tests/test_members.py::TestMembers::test_membership_lock_after_first_contribution PASSED [ 43%]
tests/test_money.py::TestMoneyParsing::test_valid_integer_amount PASSED  [ 45%]
tests/test_money.py::TestMoneyParsing::test_valid_decimal_amount PASSED  [ 47%]
tests/test_money.py::TestMoneyParsing::test_currency_prefix_and_whitespace PASSED [ 50%]
tests/test_money.py::TestMoneyParsing::test_reject_zero_amount PASSED    [ 52%]
tests/test_money.py::TestMoneyParsing::test_reject_negative_amount PASSED [ 54%]
tests/test_money.py::TestMoneyParsing::test_reject_more_than_two_decimal_places PASSED [ 56%]
tests/test_money.py::TestMoneyParsing::test_reject_scientific_notation PASSED [ 58%]
tests/test_money.py::TestMoneyParsing::test_reject_nan_and_infinity PASSED [ 60%]
tests/test_money.py::TestMoneyParsing::test_reject_empty_or_invalid_string PASSED [ 63%]
tests/test_money.py::TestMoneyFormatting::test_format_standard_pesewas PASSED [ 65%]
tests/test_money.py::TestMoneyFormatting::test_format_without_prefix PASSED [ 67%]
tests/test_money.py::TestMoneyFormatting::test_format_negative PASSED    [ 69%]
tests/test_money.py::TestMoneyFormatting::test_format_type_error PASSED  [ 71%]
tests/test_reports.py::TestReports::test_report_empty_group PASSED       [ 73%]
tests/test_reports.py::TestReports::test_report_active_group_with_partial_contributions PASSED [ 76%]
tests/test_reports.py::TestReports::test_report_completed_cycle PASSED   [ 78%]
tests/test_reports.py::TestReports::test_format_closing_blocked PASSED   [ 80%]
tests/test_reports.py::TestReports::test_format_closing_success PASSED   [ 82%]
tests/test_transactions.py::TestTransactionsAndRollback::test_contribution_rollback_on_failure PASSED [ 84%]
tests/test_transactions.py::TestTransactionsAndRollback::test_week_closing_atomic_rollback_on_blocked PASSED [ 86%]
tests/test_transactions.py::TestTransactionsAndRollback::test_explicit_transaction_rollback_preserves_state PASSED [ 89%]
tests/test_transactions.py::TestTransactionsAndRollback::test_concurrent_payments_prevent_overpayment PASSED [ 91%]
tests/test_week_closing.py::TestWeekClosing::test_block_week_closing_if_less_than_two_members PASSED [ 93%]
tests/test_week_closing.py::TestWeekClosing::test_block_closing_when_contributions_unpaid PASSED [ 95%]
tests/test_week_closing.py::TestWeekClosing::test_successful_week_1_closing_and_payout PASSED [ 97%]
tests/test_week_closing.py::TestWeekClosing::test_full_cycle_rotation_and_completion PASSED [100%]

============================= 46 passed in 0.84s ==============================
```
```

---

## 🤝 Contributing

Contributions, issues, and feature suggestions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m "feat: add amazing feature"`)
4. Run tests (`python -m pytest`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
<b>Built with care for the Ghanaian savings community 🇬🇭</b><br>
Contribute Together. Receive in Turn.
</div>
