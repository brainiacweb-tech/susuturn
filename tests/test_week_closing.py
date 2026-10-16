"""Unit tests for week closing, payout distribution, atomic transactions, and rotation logic."""

import pytest
from susuturn.exceptions import (
    WeekClosingBlockedError,
    CycleCompletedError,
)


class TestWeekClosing:
    """Tests covering week closing rules and pot payout."""

    def test_block_week_closing_if_less_than_two_members(self, service):
        service.create_group("Solo Susu", "50.00")
        service.add_member("Solo")
        with pytest.raises(WeekClosingBlockedError, match="At least 2 members are required"):
            service.close_week()

    def test_block_closing_when_contributions_unpaid(self, sample_group):
        service = sample_group["service"]
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "30.00")  # Esi still owes 20.00

        with pytest.raises(WeekClosingBlockedError) as exc_info:
            service.close_week()

        error = exc_info.value
        assert len(error.outstanding_members) == 1
        assert error.outstanding_members[0]["name"] == "Esi"
        assert error.outstanding_members[0]["balance_pesewas"] == 2000
        assert error.outstanding_members[0]["balance_formatted"] == "GHS 20.00"

        # Verify active week did not advance
        group = service.get_group()
        assert group.current_week == 1
        assert not group.is_completed

    def test_successful_week_1_closing_and_payout(self, sample_group):
        service = sample_group["service"]
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "50.00")

        result = service.close_week()

        assert result["closed_week"] == 1
        assert result["total_pot_pesewas"] == 15000  # 3 * 5000
        assert result["recipient_name"] == "Ama"  # Position 1
        assert not result["is_cycle_completed"]
        assert result["next_week"] == 2
        assert result["next_recipient"] == "Kofi"

        # Check DB state
        group = service.get_group()
        assert group.current_week == 2
        assert not group.is_completed

        payout = service.repo.get_payout_for_week(1)
        assert payout is not None
        assert payout.recipient_name == "Ama"
        assert payout.amount_pesewas == 15000

    def test_full_cycle_rotation_and_completion(self, sample_group):
        service = sample_group["service"]

        # Week 1: Ama receives GHS 150.00
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "50.00")
        r1 = service.close_week()
        assert r1["recipient_name"] == "Ama"
        assert r1["next_week"] == 2

        # Week 2: Kofi receives GHS 150.00
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "50.00")
        r2 = service.close_week()
        assert r2["recipient_name"] == "Kofi"
        assert r2["next_week"] == 3

        # Week 3: Esi receives GHS 150.00 (Final week)
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "50.00")
        r3 = service.close_week()
        assert r3["recipient_name"] == "Esi"
        assert r3["is_cycle_completed"]
        assert r3["next_week"] is None

        # Verify completed status
        group = service.get_group()
        assert group.is_completed

        # Verify no further contributions allowed
        with pytest.raises(CycleCompletedError, match="savings cycle has ended"):
            service.record_contribution("Ama", "50.00")

        # Verify no further close-week allowed
        with pytest.raises(CycleCompletedError, match="savings cycle has already completed"):
            service.close_week()
