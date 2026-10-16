"""Custom domain and validation exceptions for SusuTurn."""


class SusuTurnError(Exception):
    """Base exception for all SusuTurn domain and application errors."""


class ValidationError(SusuTurnError):
    """Raised when input validation fails (e.g. invalid money, blank name)."""


class InvalidMoneyError(ValidationError):
    """Raised when monetary amounts are malformed, negative, or imprecise."""


class GroupAlreadyExistsError(SusuTurnError):
    """Raised when attempting to create a group in an already initialized database."""


class GroupNotFoundError(SusuTurnError):
    """Raised when an operation requires an existing group, but none is found."""


class DuplicateMemberError(SusuTurnError):
    """Raised when attempting to register a member with an existing name."""


class MemberNotFoundError(SusuTurnError):
    """Raised when referencing a member that does not exist."""


class MembershipLockedError(SusuTurnError):
    """Raised when attempting to add or modify members after contributions have started."""


class CycleCompletedError(SusuTurnError):
    """Raised when attempting operations (contributions, closing) on a completed cycle."""


class WeekClosingBlockedError(SusuTurnError):
    """Raised when a week cannot be closed due to unpaid member contributions or rule violations."""

    def __init__(self, message: str, outstanding_members: list[dict] | None = None):
        super().__init__(message)
        self.outstanding_members = outstanding_members or []


class ExcessivePaymentError(SusuTurnError):
    """Raised when a contribution exceeds the member's remaining balance for the active week."""
