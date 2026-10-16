"""Database access repository for SusuTurn entities."""

from datetime import datetime, timezone
import sqlite3
from typing import Optional

from susuturn.models import SavingsGroup, Member, Contribution, Payout, MemberWeekStatus


def _current_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class SusuRepository:
    """Encapsulates all database queries and writes for the SusuTurn application."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ------------------ Group Operations ------------------ #

    def get_group(self) -> Optional[SavingsGroup]:
        """Fetch the single savings group, if one exists."""
        cursor = self.conn.execute(
            """
            SELECT id, name, weekly_contribution_pesewas, created_at, current_week, is_completed
            FROM savings_groups
            WHERE id = 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SavingsGroup(
            id=row["id"],
            name=row["name"],
            weekly_contribution_pesewas=row["weekly_contribution_pesewas"],
            created_at=row["created_at"],
            current_week=row["current_week"],
            is_completed=bool(row["is_completed"]),
        )

    def create_group(self, name: str, weekly_pesewas: int) -> SavingsGroup:
        """Create the single savings group record."""
        now = _current_timestamp()
        self.conn.execute(
            """
            INSERT INTO savings_groups (id, name, weekly_contribution_pesewas, created_at, current_week, is_completed)
            VALUES (1, ?, ?, ?, 1, 0)
            """,
            (name, weekly_pesewas, now),
        )
        return SavingsGroup(
            id=1,
            name=name,
            weekly_contribution_pesewas=weekly_pesewas,
            created_at=now,
            current_week=1,
            is_completed=False,
        )

    def advance_week(self, next_week: int, is_completed: bool = False) -> None:
        """Advance the current week number and update cycle completion status."""
        self.conn.execute(
            """
            UPDATE savings_groups
            SET current_week = ?, is_completed = ?
            WHERE id = 1
            """,
            (next_week, 1 if is_completed else 0),
        )

    # ------------------ Member Operations ------------------ #

    def add_member(self, name: str) -> Member:
        """Add a new member with the next sequential joining position."""
        now = _current_timestamp()
        normalized = name.strip().lower()

        # Determine next joining position
        cursor = self.conn.execute("SELECT COALESCE(MAX(joining_position), 0) + 1 AS next_pos FROM members")
        next_pos = cursor.fetchone()["next_pos"]

        cursor = self.conn.execute(
            """
            INSERT INTO members (name, normalized_name, joining_position, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name.strip(), normalized, next_pos, now),
        )
        member_id = cursor.lastrowid
        return Member(
            id=member_id,
            name=name.strip(),
            joining_position=next_pos,
            created_at=now,
        )

    def get_member_by_name(self, name: str) -> Optional[Member]:
        """Lookup a member by name (case-insensitive and trimmed)."""
        normalized = name.strip().lower()
        cursor = self.conn.execute(
            """
            SELECT id, name, joining_position, created_at
            FROM members
            WHERE normalized_name = ?
            """,
            (normalized,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Member(
            id=row["id"],
            name=row["name"],
            joining_position=row["joining_position"],
            created_at=row["created_at"],
        )

    def get_member_by_position(self, position: int) -> Optional[Member]:
        """Lookup a member by their joining position."""
        cursor = self.conn.execute(
            """
            SELECT id, name, joining_position, created_at
            FROM members
            WHERE joining_position = ?
            """,
            (position,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Member(
            id=row["id"],
            name=row["name"],
            joining_position=row["joining_position"],
            created_at=row["created_at"],
        )

    def get_all_members(self) -> list[Member]:
        """Return all registered members ordered strictly by joining_position."""
        cursor = self.conn.execute(
            """
            SELECT id, name, joining_position, created_at
            FROM members
            ORDER BY joining_position ASC
            """
        )
        return [
            Member(
                id=row["id"],
                name=row["name"],
                joining_position=row["joining_position"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]

    def count_members(self) -> int:
        """Return total count of registered members."""
        cursor = self.conn.execute("SELECT COUNT(*) AS total FROM members")
        return cursor.fetchone()["total"]

    # ------------------ Contribution Operations ------------------ #

    def add_contribution(self, member_id: int, week_number: int, amount_pesewas: int) -> Contribution:
        """Record an individual contribution transaction."""
        now = _current_timestamp()
        cursor = self.conn.execute(
            """
            INSERT INTO contributions (member_id, week_number, amount_pesewas, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, week_number, amount_pesewas, now),
        )
        return Contribution(
            id=cursor.lastrowid,
            member_id=member_id,
            week_number=week_number,
            amount_pesewas=amount_pesewas,
            created_at=now,
        )

    def get_member_contributed_amount(self, member_id: int, week_number: int) -> int:
        """Return the sum of pesewas contributed by a member for a given week."""
        cursor = self.conn.execute(
            """
            SELECT COALESCE(SUM(amount_pesewas), 0) AS total
            FROM contributions
            WHERE member_id = ? AND week_number = ?
            """,
            (member_id, week_number),
        )
        return cursor.fetchone()["total"]

    def count_total_contributions(self) -> int:
        """Count total contribution records in database (used for membership locking)."""
        cursor = self.conn.execute("SELECT COUNT(*) AS total FROM contributions")
        return cursor.fetchone()["total"]

    def get_member_week_statuses(self, week_number: int, target_pesewas: int) -> list[MemberWeekStatus]:
        """Return contribution status for each member for the given week, ordered by position."""
        members = self.get_all_members()
        statuses = []
        for m in members:
            paid = self.get_member_contributed_amount(m.id, week_number)
            balance = max(0, target_pesewas - paid)
            statuses.append(
                MemberWeekStatus(
                    member_id=m.id,
                    member_name=m.name,
                    joining_position=m.joining_position,
                    target_pesewas=target_pesewas,
                    paid_pesewas=paid,
                    balance_pesewas=balance,
                )
            )
        return statuses

    # ------------------ Payout Operations ------------------ #

    def record_payout(self, week_number: int, recipient_member_id: int, amount_pesewas: int) -> Payout:
        """Record a weekly payout."""
        now = _current_timestamp()
        cursor = self.conn.execute(
            """
            INSERT INTO payouts (week_number, recipient_member_id, amount_pesewas, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (week_number, recipient_member_id, amount_pesewas, now),
        )
        # Fetch recipient name
        member = self.conn.execute("SELECT name FROM members WHERE id = ?", (recipient_member_id,)).fetchone()
        name = member["name"] if member else "Unknown"
        return Payout(
            id=cursor.lastrowid,
            week_number=week_number,
            recipient_member_id=recipient_member_id,
            recipient_name=name,
            amount_pesewas=amount_pesewas,
            created_at=now,
        )

    def get_payout_for_week(self, week_number: int) -> Optional[Payout]:
        """Fetch payout for a given week."""
        cursor = self.conn.execute(
            """
            SELECT p.id, p.week_number, p.recipient_member_id, m.name AS recipient_name, p.amount_pesewas, p.created_at
            FROM payouts p
            JOIN members m ON p.recipient_member_id = m.id
            WHERE p.week_number = ?
            """,
            (week_number,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Payout(
            id=row["id"],
            week_number=row["week_number"],
            recipient_member_id=row["recipient_member_id"],
            recipient_name=row["recipient_name"],
            amount_pesewas=row["amount_pesewas"],
            created_at=row["created_at"],
        )

    def get_all_payouts(self) -> list[Payout]:
        """Return all payouts ordered by week number."""
        cursor = self.conn.execute(
            """
            SELECT p.id, p.week_number, p.recipient_member_id, m.name AS recipient_name, p.amount_pesewas, p.created_at
            FROM payouts p
            JOIN members m ON p.recipient_member_id = m.id
            ORDER BY p.week_number ASC
            """
        )
        return [
            Payout(
                id=row["id"],
                week_number=row["week_number"],
                recipient_member_id=row["recipient_member_id"],
                recipient_name=row["recipient_name"],
                amount_pesewas=row["amount_pesewas"],
                created_at=row["created_at"],
            )
            for row in cursor.fetchall()
        ]
