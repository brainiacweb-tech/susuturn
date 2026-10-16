"""Unit tests for database transaction integrity and rollback behavior."""

import pytest
from susuturn.database import transaction
from susuturn.exceptions import ExcessivePaymentError, WeekClosingBlockedError


class TestTransactionsAndRollback:
    """Tests ensuring atomicity and clean rollbacks on errors."""

    def test_contribution_rollback_on_failure(self, sample_group):
        service = sample_group["service"]
        conn = sample_group["service"].conn

        # Ama contributes 30.00
        service.record_contribution("Ama", "30.00")
        assert service.repo.get_member_contributed_amount(sample_group["members"][0].id, 1) == 3000

        # Attempt an excessive payment of 40.00 (which exceeds the 20.00 remaining balance)
        with pytest.raises(ExcessivePaymentError):
            service.record_contribution("Ama", "40.00")

        # Total paid must remain exactly 3000 pesewas; no partial mutation or dirty record should exist
        assert service.repo.get_member_contributed_amount(sample_group["members"][0].id, 1) == 3000

    def test_week_closing_atomic_rollback_on_blocked(self, sample_group):
        service = sample_group["service"]
        # Ama and Kofi pay in full, Esi only pays 20.00
        service.record_contribution("Ama", "50.00")
        service.record_contribution("Kofi", "50.00")
        service.record_contribution("Esi", "20.00")

        # Attempt to close week
        with pytest.raises(WeekClosingBlockedError):
            service.close_week()

        # Confirm no payout record was inserted and week is still 1
        payouts = service.repo.get_all_payouts()
        assert len(payouts) == 0

        group = service.get_group()
        assert group.current_week == 1
        assert not group.is_completed

    def test_explicit_transaction_rollback_preserves_state(self, sample_group):
        service = sample_group["service"]
        conn = service.conn

        # Test transaction context manager directly
        with pytest.raises(RuntimeError):
            with transaction(conn):
                service.repo.add_contribution(sample_group["members"][0].id, 1, 1000)
                raise RuntimeError("Simulated crash mid-transaction")

        # Confirm 1000 pesewas contribution rolled back
        assert service.repo.get_member_contributed_amount(sample_group["members"][0].id, 1) == 0
