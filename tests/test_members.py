"""Unit tests for member registration and management rules."""

import pytest
from susuturn.exceptions import (
    ValidationError,
    DuplicateMemberError,
    MembershipLockedError,
    GroupAlreadyExistsError,
    GroupNotFoundError,
)


class TestMembers:
    """Tests for member creation and ordering."""

    def test_create_savings_group(self, service):
        group = service.create_group("KNUST Friends Susu", "50.00")
        assert group.id == 1
        assert group.name == "KNUST Friends Susu"
        assert group.weekly_contribution_pesewas == 5000
        assert group.current_week == 1
        assert not group.is_completed

    def test_reject_second_group_creation(self, service):
        service.create_group("First Group", "50.00")
        with pytest.raises(GroupAlreadyExistsError, match="already exists"):
            service.create_group("Second Group", "100.00")

    def test_add_members_preserves_joining_order(self, service):
        service.create_group("KNUST Friends Susu", "50.00")
        m1 = service.add_member("Ama")
        m2 = service.add_member("Kofi")
        m3 = service.add_member("Esi")

        assert m1.joining_position == 1
        assert m2.joining_position == 2
        assert m3.joining_position == 3

        all_members = service.get_all_members()
        assert len(all_members) == 3
        assert [m.name for m in all_members] == ["Ama", "Kofi", "Esi"]
        assert [m.joining_position for m in all_members] == [1, 2, 3]

    def test_reject_blank_or_whitespace_name(self, service):
        service.create_group("KNUST Friends Susu", "50.00")
        with pytest.raises(ValidationError, match="cannot be blank"):
            service.add_member("")
        with pytest.raises(ValidationError, match="cannot be blank"):
            service.add_member("    ")

    def test_trim_surrounding_whitespace(self, service):
        service.create_group("KNUST Friends Susu", "50.00")
        m = service.add_member("  Kwame  ")
        assert m.name == "Kwame"

    def test_reject_duplicate_member_names_case_insensitive(self, service):
        service.create_group("KNUST Friends Susu", "50.00")
        service.add_member("Ama")

        with pytest.raises(DuplicateMemberError, match="already exists"):
            service.add_member("Ama")

        with pytest.raises(DuplicateMemberError, match="already exists"):
            service.add_member("ama")

        with pytest.raises(DuplicateMemberError, match="already exists"):
            service.add_member("  AMA  ")

    def test_add_member_requires_group(self, service):
        with pytest.raises(GroupNotFoundError, match="No savings group found"):
            service.add_member("Ama")

    def test_membership_lock_after_first_contribution(self, sample_group):
        service = sample_group["service"]
        # Record one contribution
        service.record_contribution("Ama", "20.00")

        # Attempt to add another member
        with pytest.raises(MembershipLockedError, match="Membership is locked"):
            service.add_member("Akua")
