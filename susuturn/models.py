"""Data models for SusuTurn entities."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SavingsGroup:
    """Represents the single rotating savings group in the database."""
    id: int
    name: str
    weekly_contribution_pesewas: int
    created_at: str
    current_week: int
    is_completed: bool


@dataclass(frozen=True)
class Member:
    """Represents a member in the rotating savings group."""
    id: int
    name: str
    joining_position: int
    created_at: str


@dataclass(frozen=True)
class Contribution:
    """Represents an individual contribution transaction."""
    id: int
    member_id: int
    week_number: int
    amount_pesewas: int
    created_at: str


@dataclass(frozen=True)
class Payout:
    """Represents a weekly payout to a recipient."""
    id: int
    week_number: int
    recipient_member_id: int
    recipient_name: str
    amount_pesewas: int
    created_at: str


@dataclass(frozen=True)
class MemberWeekStatus:
    """Summary of a member's contribution status for a specific week."""
    member_id: int
    member_name: str
    joining_position: int
    target_pesewas: int
    paid_pesewas: int
    balance_pesewas: int

    @property
    def is_paid_in_full(self) -> bool:
        return self.balance_pesewas == 0
