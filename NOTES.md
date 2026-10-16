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

### 2.5 Strict Atomic Transactions & Concurrency Safety
- **Decision:** All critical read-validate-write sequences (balance checking before payment, membership locking checks before adding a member, and member debt checking before closing a week) are wrapped in `BEGIN IMMEDIATE` SQLite transactions.
- **Rationale:**
  - In concurrent CLI invocations (e.g., two users contributing simultaneously), reading the remaining balance outside a transaction creates a time-of-check to time-of-use (TOCTOU) race condition that could permit combined overpayment.
  - By acquiring an immediate write lock before checking the member's current contributions, subsequent writes from concurrent processes are serialized, guaranteeing that total contributions never exceed the weekly target.
  - Weekly closing is completely atomic: debt validation, payout insertion, and week advancement succeed together or rollback completely.

---

## 3. Database Schema Design

The SQLite schema leverages SQLite's relational integrity features:
- **`PRAGMA foreign_keys = ON`**: Enforced on every connection.
- **`savings_groups`**: Enforces a single group row (`id = 1`), storing `weekly_contribution_pesewas`, `current_week`, and `is_completed`.
- **`members`**: Stores `name`, case-insensitive unique `normalized_name`, unique `joining_position`, and creation timestamp.
- **`contributions`**: Stores individual payments linked via foreign keys to `members(id)`, referencing `week_number` and integer `amount_pesewas`.
- **`payouts`**: Stores weekly pot distributions with `UNIQUE` constraints on both `week_number` and `recipient_member_id`.

---

## 4. Current Limitations

While SusuTurn meets all requirements of the specification, the current architecture intentionally incorporates specific design tradeoffs:

1. **Single Rotation Limit per SQLite File:**
   Starting a subsequent cycle requires spinning up a new database file via `--db <filename>`. There is currently no multi-cycle rollover entity in the database schema.
2. **Fixed Weekly Schedule Only:**
   The frequency is strictly weekly. Daily or monthly susu schemes (common among market traders in Makola and Kejetia) are not currently supported by the configuration model.
3. **No Dynamic Member Swap or Emergency Reordering:**
   If a member faces an emergency and needs an earlier payout turn, swapping positions requires manual database intervention because joining positions are immutable.
4. **Local SQLite Concurrency Boundary:**
   SQLite file locking works well for single-user CLI execution and local multi-process access, but does not scale to high-concurrency client-server web deployments.

---

## 5. Future Enhancements (Given More Time)

If expanded beyond the assessment scope into an enterprise-grade financial management system, the following enhancements would be prioritized:

1. **Turn-Swapping Protocol:**
   Implement a cryptographically verifiable mutual-consent turn exchange mechanism (`susuturn swap-turn --from "Ama" --to "Kofi"`), allowing members to trade turns if agreed by both parties without altering overall cycle mechanics.
2. **Multi-Cycle Support & Rollover:**
   Introduce a `cycles` table parent entity so that a single group can seamlessly advance from Cycle 1 to Cycle 2, carrying forward historical member reputation and attendance metrics.
3. **Mobile Money (MoMo) Webhook Integration:**
   Integrate with Ghanaian payment gateways (Paystack, Hubtel, or direct MTN MoMo / Telecel Cash APIs) to automatically ingest and reconcile SMS or webhook payments directly into `contributions`.
4. **Variable Frequency & Configurable Pots:**
   Support daily, bi-weekly, or monthly intervals (`--frequency daily`), matching real-world market artisan practices.
5. **CSV / Excel Audit Export:**
   Add a `susuturn export --format csv` command to generate downloadable financial audit sheets for group treasurers.
6. **Automated Reminders:**
   Integrate Twilio or local SMS providers to send automated WhatsApp / SMS reminders to members with outstanding balances before weekly closing deadlines.

---

## 6. Testing Strategy

The automated test suite in `tests/` uses `pytest` and contains 44 tests across 7 dedicated test modules:
- `test_money.py`: Validates string parsing, integer conversion, rejection of malformed/scientific/negative inputs, and formatting.
- `test_members.py`: Validates group creation, membership sequencing, whitespace stripping, case-insensitive uniqueness, and membership locking.
- `test_contributions.py`: Validates single payments, partial payments, cumulative balance checks, and rejection of overpayments.
- `test_week_closing.py`: Validates blocking on unpaid balances, pot calculation, payout assignment, week advancing, and cycle completion.
- `test_transactions.py`: Validates atomic rollbacks, excessive payment rollbacks, blocked week rollbacks, and transaction isolation.
- `test_reports.py`: Validates group summaries, contribution tables, payout histories, and upcoming recipient displays.
- `test_cli.py`: End-to-end integration tests executing command-line dispatches against temporary databases.
