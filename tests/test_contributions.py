"""Unit tests for contribution recording and balance tracking."""

import pytest
from susuturn.exceptions import (
    MemberNotFoundError,
    ExcessivePaymentError,
    InvalidMoneyError,
    CycleCompletedError,
)


class TestContributions:
    """Tests covering member payments and rules."""

    def test_record_single_full_contribution(self, sample_group):
        service = sample_group["service"]
        contrib = service.record_contribution("Ama", "50.00")
        assert contrib.amount_pesewas == 5000
        assert contrib.week_number == 1

        paid = service.repo.get_member_contributed_amount(contrib.member_id, 1)
        assert paid == 5000

    def test_record_partial_contributions_and_exact_sum(self, sample_group):
        service = sample_group["service"]
        m2 = sample_group["members"][1]  # Kofi

        c1 = service.record_contribution("Kofi", "20.00")
        assert c1.amount_pesewas == 2050 - 50  # 2000
        assert service.repo.get_member_contributed_amount(m2.id, 1) == 2000

        c2 = service.record_contribution("Kofi", "30.00")
        assert c2.amount_pesewas == 3000
        assert service.repo.get_member_contributed_amount(m2.id, 1) == 5000

    def test_reject_unknown_member_contribution(self, sample_group):
        service = sample_group["service"]
        with pytest.raises(MemberNotFoundError, match="is not registered"):
            service.record_contribution("NonExistentMember", "50.00")

    def test_reject_zero_or_negative_contribution(self, sample_group):
        service = sample_group["service"]
        with pytest.raises(InvalidMoneyError, match="greater than zero"):
            service.record_contribution("Ama", "0.00")

        with pytest.raises(InvalidMoneyError, match="positive"):
            service.record_contribution("Ama", "-10.00")

    def test_reject_payment_exceeding_remaining_balance(self, sample_group):
        service = sample_group["service"]
        # Try paying 60 when target is 50
        with pytest.raises(ExcessivePaymentError, match="exceeds remaining balance"):
            service.record_contribution("Ama", "60.00")

        # Pay 40, then try paying 20 when only 10 is owed
        service.record_contribution("Ama", "40.00")
        with pytest.raises(ExcessivePaymentError, match="exceeds remaining balance"):
            service.record_contribution("Ama", "20.00")

    def test_reject_payment_when_already_fully_paid(self, sample_group):
        service = sample_group["service"]
        service.record_contribution("Ama", "50.00")

        with pytest.raises(ExcessivePaymentError, match="already paid the required weekly contribution"):
            service.record_contribution("Ama", "10.00")
