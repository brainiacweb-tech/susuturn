# SusuTurn — Design Notes & Architectural Decisions

## 1. Domain Modeling: The Ghanaian Susu Model

A **susu** is a traditional informal rotating savings and credit association (ROSCA) widely practiced in Ghana and West Africa. In a susu group:
1. Every member contributes a fixed, agreed-upon amount at regular periodic intervals (typically weekly).
2. At the end of each round (week), the entire pooled sum ("the pot") is handed over to one member in full.
3. Every member takes a turn receiving the pot until everyone has received their scheduled payout exactly once.

SusuTurn digitizes this rotation into a reliable, verifiable command-line tool.

---

## 2. Core Architectural Decisions

### 2.1 Integer Pesewas for Monetary Precision
- **The Problem:** IEEE 754 binary floating-point representations (`float` in Python) introduce rounding anomalies (e.g. `0.1 + 0.2 = 0.30000000000000004`). In financial systems, accumulating rounding errors can cause imbalances between total contributions and payouts.
- **The Solution:** SusuTurn parses all user-entered currency values strictly into integer **pesewas** (1 Ghana Cedi [GHS] = 100 pesewas) upon input.
- **Input Validation:** Amounts with more than 2 decimal places (such as `50.123`) are rejected with an explicit error rather than silently rounded. Scientific notation (`1e5`), negative numbers, `NaN`, and `Infinity` are rejected upfront using string inspection and regular expressions. All arithmetic operations (sums, differences, balances) are executed purely as integer operations.

### 2.2 Single Rotation Lifecycle per Database
- **Decision:** The system models exactly one complete savings rotation per database file.
- **Rationale:** Simplicity, auditability, and data isolation. By enforcing one group per database (`id INTEGER PRIMARY KEY CHECK (id = 1)`), each savings cycle remains an immutable historical record once completed. To run a new cycle or a different circle of participants, users simply specify another database path using the `--db` option (e.g., `--db year2027.db`).

### 2.3 Permanent Joining Order Determines Payout Sequence
- **Decision:** Payout recipient order is determined strictly by the sequential joining position (`joining_position = 1, 2, 3...`), never alphabetically or randomly.
- **Rationale:** Traditional susu groups award turns based on the agreed lineup at formation. In SusuTurn, the recipient for Week $W$ is guaranteed to be the member with `joining_position = W`.

### 2.4 Strict Membership Locking
- **Decision:** Once the first contribution is recorded for any member, the group membership is locked permanently. No members may be added, deleted, or reordered.
- **Rationale:** In a rotating savings group, the total pot size ($N \times \text{weekly\_amount}$) and the total duration ($N$ weeks) are fixed by the number of members $N$. Adding or removing members midway would alter the pot amount and disrupt the rotation schedule for members who already paid or received their turns. Locking membership at the moment money begins moving ensures mathematical and contractual consistency.

### 2.5 Strict Atomic Week Closing
- **Decision:** Closing a week requires every member to have paid their weekly contribution in full. Week closing records the payout and advances the current week inside an immediate SQLite transaction.
- **Rationale:**
  - If any member has an outstanding balance, closing is blocked and the exact unpaid amounts are displayed. The active week does not advance.
  - Transactions ensure that recording the payout and updating the group's current week / completion status either both commit or neither commits, eliminating partial or orphaned states.
  - SQLite table constraints (`UNIQUE` on `payouts.week_number` and `payouts.recipient_member_id`) structurally prevent double-payouts to the same member.

---

## 3. Database Schema Design

The SQLite schema leverages SQLite's relational integrity features:
- **`PRAGMA foreign_keys = ON`**: Enforced on every connection.
- **`savings_groups`**: Enforces a single group row (`id = 1`), storing `weekly_contribution_pesewas`, `current_week`, and `is_completed`.
- **`members`**: Stores `name`, case-insensitive unique `normalized_name`, unique `joining_position`, and creation timestamp.
- **`contributions`**: Stores individual payments linked via foreign keys to `members(id)`, referencing `week_number` and integer `amount_pesewas`.
- **`payouts`**: Stores weekly pot distributions with `UNIQUE` constraints on both `week_number` and `recipient_member_id`.

---

## 4. Testing Strategy

The automated test suite in `tests/` uses `pytest` and contains 41 tests across 6 dedicated test modules:
- `test_money.py`: Validates string parsing, integer conversion, rejection of malformed/scientific/negative inputs, and formatting.
- `test_members.py`: Validates group creation, membership sequencing, whitespace stripping, case-insensitive uniqueness, and membership locking.
- `test_contributions.py`: Validates single payments, partial payments, cumulative balance checks, and rejection of overpayments.
- `test_week_closing.py`: Validates blocking on unpaid balances, pot calculation, payout assignment, week advancing, and cycle completion.
- `test_reports.py`: Validates group summaries, contribution tables, payout histories, and upcoming recipient displays.
- `test_cli.py`: End-to-end integration tests executing command-line dispatches against temporary databases.
