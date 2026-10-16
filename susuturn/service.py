"""Business logic and service orchestration for SusuTurn."""

import sqlite3
from typing import Optional

from susuturn.database import transaction
from susuturn.exceptions import (
    SusuTurnError,
    GroupAlreadyExistsError,
    GroupNotFoundError,
    ValidationError,
    DuplicateMemberError,
    MemberNotFoundError,
    MembershipLockedError,
    CycleCompletedError,
    ExcessivePaymentError,
    WeekClosingBlockedError,
)
from susuturn.models import SavingsGroup, Member, Contribution, Payout, MemberWeekStatus
from susuturn.money import parse_ghs_to_pesewas, format_pesewas_to_ghs
from susuturn.repository import SusuRepository


class SusuService:
    """Encapsulates all domain rules, invariants, and operations for SusuTurn."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.repo = SusuRepository(conn)

    # ------------------ Group Operations ------------------ #

    def create_group(self, name: str, weekly_amount: str | int | float) -> SavingsGroup:
        """Create a new savings group.

        Rules:
        - Group name must not be empty or whitespace-only.
        - Weekly contribution must be greater than zero and max 2 decimal places.
        - Only one group allowed per database.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValidationError("Group name cannot be blank or empty.")

        existing = self.repo.get_group()
        if existing is not None:
            raise GroupAlreadyExistsError(
                f"A savings group named '{existing.name}' already exists in this database. "
                "Only one savings group is permitted per database."
            )

        weekly_pesewas = parse_ghs_to_pesewas(weekly_amount)

        with transaction(self.conn):
            return self.repo.create_group(clean_name, weekly_pesewas)

    def get_group(self) -> SavingsGroup:
        """Get the current savings group, raising an error if uninitialized."""
        group = self.repo.get_group()
        if group is None:
            raise GroupNotFoundError(
                "No savings group found. Initialize the group first using 'susuturn create --name <NAME> --weekly <AMOUNT>'."
            )
        return group

    # ------------------ Member Operations ------------------ #

    def add_member(self, name: str) -> Member:
        """Register a new member in the savings group.

        Rules:
        - Group must exist.
        - Membership becomes locked after the first contribution is recorded.
        - Member name must not be blank or whitespace-only.
        - Reject duplicate names (case-insensitive).
        - Assign permanent joining position.
        """
        self.get_group()  # Ensure group exists

        clean_name = (name or "").strip()
        if not clean_name:
            raise ValidationError("Member name cannot be blank or whitespace-only.")

        # Check membership lock
        total_contributions = self.repo.count_total_contributions()
        if total_contributions > 0:
            raise MembershipLockedError(
                "Membership is locked because contributions have already started. "
                "No new members can join or leave the group."
            )

        # Check duplicate name
        existing_member = self.repo.get_member_by_name(clean_name)
        if existing_member is not None:
            raise DuplicateMemberError(
                f"Member with name '{clean_name}' already exists (as '{existing_member.name}', Position #{existing_member.joining_position})."
            )

        with transaction(self.conn):
            return self.repo.add_member(clean_name)

    def get_all_members(self) -> list[Member]:
        """Return all registered members ordered by joining position."""
        return self.repo.get_all_members()

    # ------------------ Contribution Operations ------------------ #

    def record_contribution(self, member_name: str, amount: str | int | float) -> Contribution:
        """Record a weekly contribution for a member.

        Rules:
        - Group must exist and cycle must not be completed.
        - Member must exist.
        - Amount must be positive and have at most 2 decimal places.
        - Member payment cannot exceed their remaining balance for the active week.
        """
        group = self.get_group()
        if group.is_completed:
            raise CycleCompletedError("The savings cycle has ended. No further contributions are accepted.")

        clean_name = (member_name or "").strip()
        if not clean_name:
            raise ValidationError("Member name cannot be blank.")

        member = self.repo.get_member_by_name(clean_name)
        if member is None:
            raise MemberNotFoundError(f"Member '{clean_name}' is not registered in this savings group.")

        amount_pesewas = parse_ghs_to_pesewas(amount)

        # Check existing contributions for the active week
        already_paid = self.repo.get_member_contributed_amount(member.id, group.current_week)
        remaining_balance = group.weekly_contribution_pesewas - already_paid

        if remaining_balance <= 0:
            raise ExcessivePaymentError(
                f"Member '{member.name}' has already paid the required weekly contribution of "
                f"{format_pesewas_to_ghs(group.weekly_contribution_pesewas)} for Week {group.current_week} in full."
            )

        if amount_pesewas > remaining_balance:
            raise ExcessivePaymentError(
                f"Payment of {format_pesewas_to_ghs(amount_pesewas)} exceeds remaining balance. "
                f"Member '{member.name}' only owes {format_pesewas_to_ghs(remaining_balance)} for Week {group.current_week}."
            )

        with transaction(self.conn):
            return self.repo.add_contribution(member.id, group.current_week, amount_pesewas)

    # ------------------ Week Closing Operations ------------------ #

    def close_week(self) -> dict:
        """Close the active week and pay out the pot.

        Rules:
        - Group must exist and cycle must not be completed.
        - Must have at least two members before closing Week 1.
        - All members must have paid their weekly contribution in full.
        - Payout goes to member at joining position matching current week.
        - Payout amount = Total members * weekly contribution.
        - Week advance and payout record must be atomically executed.
        - If active week == total members, mark cycle as completed.
        """
        group = self.get_group()
        if group.is_completed:
            raise CycleCompletedError("The savings cycle has already completed.")

        members = self.repo.get_all_members()
        member_count = len(members)

        if member_count < 2:
            raise WeekClosingBlockedError(
                f"At least 2 members are required to run a savings group. Currently only {member_count} registered."
            )

        active_week = group.current_week

        # Check contribution status of all members
        statuses = self.repo.get_member_week_statuses(active_week, group.weekly_contribution_pesewas)
        unpaid = [s for s in statuses if not s.is_paid_in_full]

        if unpaid:
            outstanding_details = [
                {
                    "name": s.member_name,
                    "position": s.joining_position,
                    "paid_pesewas": s.paid_pesewas,
                    "balance_pesewas": s.balance_pesewas,
                    "balance_formatted": format_pesewas_to_ghs(s.balance_pesewas),
                }
                for s in unpaid
            ]
            raise WeekClosingBlockedError(
                f"Cannot close Week {active_week}. Some members have outstanding balances.",
                outstanding_members=outstanding_details,
            )

        # Determine recipient by joining position matching current week
        recipient = self.repo.get_member_by_position(active_week)
        if recipient is None:
            raise SusuTurnError(f"No recipient found at joining position {active_week}.")

        total_pot_pesewas = member_count * group.weekly_contribution_pesewas
        is_final_week = (active_week == member_count)
        next_week = active_week if is_final_week else active_week + 1

        with transaction(self.conn):
            payout = self.repo.record_payout(
                week_number=active_week,
                recipient_member_id=recipient.id,
                amount_pesewas=total_pot_pesewas,
            )
            self.repo.advance_week(next_week=next_week, is_completed=is_final_week)

        # Identify next recipient if cycle is not completed
        next_recipient_name = None
        if not is_final_week:
            next_member = self.repo.get_member_by_position(next_week)
            if next_member:
                next_recipient_name = next_member.name

        return {
            "closed_week": active_week,
            "total_pot_pesewas": total_pot_pesewas,
            "recipient_name": recipient.name,
            "recipient_position": recipient.joining_position,
            "is_cycle_completed": is_final_week,
            "next_week": next_week if not is_final_week else None,
            "next_recipient": next_recipient_name,
        }

    # ------------------ Report Generation Data ------------------ #

    def get_group_report_data(self) -> dict:
        """Fetch all aggregated data required for generating the comprehensive group report."""
        group = self.get_group()
        members = self.repo.get_all_members()
        total_members = len(members)
        total_pot_pesewas = total_members * group.weekly_contribution_pesewas

        # Active week status
        member_statuses = self.repo.get_member_week_statuses(
            group.current_week, group.weekly_contribution_pesewas
        )

        # Payout history
        payouts = self.repo.get_all_payouts()

        # Next recipient if active
        next_recipient = None
        if not group.is_completed:
            target_pos = group.current_week
            rec_member = self.repo.get_member_by_position(target_pos)
            if rec_member:
                next_recipient = rec_member.name

        return {
            "group": group,
            "total_members": total_members,
            "total_pot_pesewas": total_pot_pesewas,
            "member_statuses": member_statuses,
            "payouts": payouts,
            "next_recipient": next_recipient,
        }
