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

    def test_concurrent_payments_prevent_overpayment(self, tmp_path):
        """Simulate concurrent threads attempting simultaneous payments against the same database.

        Verifies that even when multiple processes/threads race to pay for the same member,
        the immediate transaction prevents total contributions from exceeding the weekly quota.
        """
        import concurrent.futures
        from susuturn.database import get_connection, init_db
        from susuturn.service import SusuService

        db_file = tmp_path / "concurrent_susu.db"
        conn_init = get_connection(db_file)
        init_db(conn_init)
        service_init = SusuService(conn_init)
        service_init.create_group("Concurrent Susu", "50.00")
        service_init.add_member("Ama")
        service_init.add_member("Kofi")
        conn_init.close()

        # Both workers attempt to pay 30.00 simultaneously for Ama (whose target is 50.00)
        # If there were a concurrency race, both 30.00 payments could succeed (total 60.00 > 50.00).
        # With immediate transaction locking, one will succeed and the other will be rejected
        # with ExcessivePaymentError (or sqlite3.OperationalError: database locked if busy).
        results = []

        def worker_pay(amount_str):
            conn = get_connection(db_file)
            service = SusuService(conn)
            try:
                service.record_contribution("Ama", amount_str)
                return "SUCCESS"
            except ExcessivePaymentError:
                return "EXCESSIVE_REJECTED"
            except Exception as e:
                return f"EXCEPTION: {type(e).__name__}"
            finally:
                conn.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker_pay, "30.00")
            f2 = executor.submit(worker_pay, "30.00")
            results = [f1.result(), f2.result()]

        # Exactly one payment of 30.00 must succeed, and total paid must never exceed 50.00
        conn_check = get_connection(db_file)
        svc_check = SusuService(conn_check)
        ama = svc_check.repo.get_member_by_name("Ama")
        total_paid = svc_check.repo.get_member_contributed_amount(ama.id, 1)
        conn_check.close()

        assert "SUCCESS" in results
        assert total_paid == 3000  # Exactly 30.00 was recorded; 60.00 was prevented!

